import asyncio
import contextlib
from collections import defaultdict
from datetime import datetime, timedelta
from inspect import iscoroutinefunction
from typing import Callable

import msgspec
import orjson
from pandas import bdate_range

from kiwoom import config
from kiwoom.config.candle import (
    PERIOD_TO_API_ID,
    PERIOD_TO_BODY_KEY,
    PERIOD_TO_DATA,
    PERIOD_TO_TIME_KEY,
    valid,
)
from kiwoom.config.real import Real
from kiwoom.config.trade import (
    REQUEST_LIMIT_DAYS,
)
from kiwoom.http import utils
from kiwoom.http.client import Client
from kiwoom.http.socket import Socket


class API(Client):
    """
    Request and Receive data with Kiwoom REST API
    """

    def __init__(self, host: str, appkey: str, secretkey: str):
        match host:
            case config.REAL:
                url = Socket.REAL + Socket.ENDPOINT
            case config.MOCK:
                url = Socket.MOCK + Socket.ENDPOINT
            case _:
                raise ValueError(f"Invalid host: {self.host}")

        super().__init__(host, appkey, secretkey)
        self.url = url
        self.queue = asyncio.Queue()
        self.socket: Socket = Socket(url=url, queue=self.queue)

        self._lock: asyncio.Lock = asyncio.Lock()
        self._read_socket_task: asyncio.Task = None
        self._stop_task_event: asyncio.Event = asyncio.Event()

        self.connected: bool = False
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(
            config.http.WEBSOCKET_MAX_CONCURRENCY
        )
        self._callbacks = defaultdict(
            lambda: utils.wrap_sync_callback(self._semaphore, lambda msg: print(msg))
        )
        self._add_default_callback_on_real_data()

    async def connect(self):
        await super().connect(self._appkey, self._secretkey)
        if not (token := self.token()):
            raise RuntimeError("Not connected: token is not available.")

        if self._read_socket_task and not self._read_socket_task.done():
            self._stop_task_event.set()
            self._read_socket_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._read_socket_task

        self.socket._stop.set()
        await self.socket.connect(self._session, token)

        self._stop_task_event.clear()
        self._read_socket_task = asyncio.create_task(
            self._on_receive_websocket(), name="read_socket"
        )

    async def close(self):
        # FIXME
        self._stop_task_event.set()

        await self.socket.close()
        await super().close()

    async def stock_list(self, market: str):
        """
        Get stock list of codes for given market code.

        Args:
            market (str): market code.

        Raises:
            ValueError: No data is available for given market code.

        Returns:
            dict: http response containing stock codes
        """
        endpoint = "/api/dostk/stkinfo"
        api_id = "ka10099"

        res = await self.request(endpoint, api_id, data={"mrkt_tp": market})
        body = res.json()
        if not body["list"] or len(body["list"]) <= 1:
            raise ValueError(f"Stock list is not available for market code, {market}.")
        return body

    async def candle(
        self,
        code: str,
        period: str,
        ctype: str,
        start: str = None,
        end: str = None,
    ) -> dict:
        """
        Candle chart data

        Args:
            code (str): code of stock or sector, e.g. '005930_AL'.
            period (str): period of candle, {"tick", "min", "day"}.
            ctype (str): type of stock or sector, {"stock", "sector"}.
            start (str, optional): start date in YYYYMMDD format. Defaults to None.
            end (str, optional): end date in YYYYMMDD format. Defaults to None.

        Raises:
            ValueError: Invalid 'ctype' or 'period'

        Returns:
            dict: raw candle data
        """

        ctype = ctype.lower()
        endpoint = "/api/dostk/chart"
        api_id = PERIOD_TO_API_ID[ctype][period]
        data = dict(PERIOD_TO_DATA[ctype][period])
        match ctype:
            case "stock":
                data["stk_cd"] = code
            case "sector":
                data["inds_cd"] = code
            case _:
                raise ValueError(f"'ctype' must be one of [stock, sector], not {ctype=}.")
        if period == "day":
            end = end if end else datetime.now().strftime("%Y%m%d")
            data["base_dt"] = end

        ymd: int = len("YYYYMMDD")  # 8 digit compare
        key: str = PERIOD_TO_BODY_KEY[ctype][period]
        time: str = PERIOD_TO_TIME_KEY[period]

        def should_continue(body: dict) -> bool:
            # Validate
            if not valid(body, period, ctype):
                return False
            # Request full data
            if not start:
                return True
            # Condition to continue
            chart = body[key]
            earliest = chart[-1][time][:ymd]
            return start <= earliest

        body = await self.request_until(should_continue, endpoint, api_id, data=data)
        return body

    async def trade(self, start: str, end: str = "") -> list[dict]:
        """
        계좌 체결내역 (키움증권 0343 화면)
        최근 2개월만 조회 가능

        Args:
            start (str): start date in YYYYMMDD format
            end (str, optional): end date in YYYYMMDD format

        Returns:
            list[dict]: raw trade data
        """
        endpoint = "/api/dostk/acnt"
        api_id = "kt00009"
        data = {
            "ord_dt": "",  # YYYYMMDD (Optional)
            "qry_tp": "1",  # 전체/체결
            "stk_bond_tp": "1",  # 전체/주식/채권
            "mrkt_tp": "0",  # 전체/코스피/코스닥/OTCBB/ECN
            "sell_tp": "0",  # 전체/매도/매수
            "dmst_stex_tp": "%",  # 전체/KRX/NXT/SOR
            # 'stk_cd': '',  # 종목코드 (Optional)
            # 'fr_ord_no': '',  # 시작주문번호 (Optional)
        }

        today = datetime.today()
        start = datetime.strptime(start, "%Y%m%d")
        start = max(start, today - timedelta(days=REQUEST_LIMIT_DAYS))
        end = datetime.strptime(end, "%Y%m%d") if end else datetime.today()
        end = min(end, datetime.today())

        trs = []
        key = "acnt_ord_cntr_prst_array"
        for bday in bdate_range(start, end):
            dic = dict(data)
            dic["ord_dt"] = bday.strftime("%Y%m%d")  # manually set ord_dt
            body = await self.request_until(lambda x: True, endpoint, api_id, data=dic)
            if key in body:
                # Append order date to each record
                for rec in body[key]:
                    rec["ord_dt"] = bday.strftime("%Y-%m-%d")
                trs.extend(body[key])
        return trs

    def add_callback_on_real_data(self, real_type: str, callback: Callable) -> None:
        """
        Add callback function on live stream websocket data where trnm is 'REAL'.

        Suppose that fn = lambda msg: print(msg), which takes msg and simply prints.
        - add_callback_on_real_data(real_type='OB', fn=fn)
            printing is applied when tick data(type 'OB') has been received.

        You may add callback function on 'PING' and 'LOGIN' as well,
        by setting real_type to 'PING' or 'LOGIN'.

        Asynchronous callback function is recommended. Async and sync callback
        functions are both running in background, not in blocking way.

        If async callback function wrapped with lambda function, it will never
        be awaited. Use 'async def wrapper(callback: Callable)' instead.

        Args:
            real_type (str, None): real type described in Kiwoom REST API.
            callback (Callable): callback function takes raw msg str as an argument
        """

        real_type = real_type.upper()
        # Asnyc
        if iscoroutinefunction(callback):
            self._callbacks[real_type] = utils.wrap_async_callback(self._semaphore, callback)
        # Sync Callback
        else:
            self._callbacks[real_type] = utils.wrap_sync_callback(self._semaphore, callback)

    def _add_default_callback_on_real_data(self) -> None:
        """
        Add default callback functions on real data receive.
        """

        # Ping
        async def callback_on_ping(raw: str):
            await self.socket.send(raw)

        self.add_callback_on_real_data(real_type="PING", callback=callback_on_ping)

        # Login
        def callback_on_login(raw: str):
            msg = orjson.loads(raw)
            if msg.get("return_code") != 0:
                raise RuntimeError(f"Login failed with return_code not zero, {msg}.")
            print(msg)

        self.add_callback_on_real_data(real_type="LOGIN", callback=callback_on_login)

    async def _on_receive_websocket(self) -> None:
        """
        Receive websocket data and dispatch to the callback function.
        Decoder patially checks 'trnm' and 'type' in order to speed up.
        Note that the argument to callback function is raw string, not decoded data.

        Raises:
            Exception: Exception raised by the callback function or decoder
        """
        decoder = msgspec.json.Decoder(type=Real)
        while not self._stop_task_event.is_set():
            try:
                raw: str = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                msg = decoder.decode(raw)  # partially decoded for speed up
                match msg.trnm:
                    case "REAL":
                        for data in msg.data:
                            asyncio.create_task(self._callbacks[data.type](raw))
                    case _:
                        asyncio.create_task(self._callbacks[msg.trnm](raw))

            except Exception as err:
                await self.close()
                raise Exception("Failed to handling websocket data.") from err

            finally:
                self.queue.task_done()

    async def register_tick(
        self,
        grp_no: str,
        codes: list[str],
        refresh: str = "1",
    ) -> None:
        """
        (실시간시세 > 주식체결 '0B')
        Register transactions with given grp_no and codes with refresh option.

        Args:
            grp_no (str): 그룹번호
            codes (list[str]): 종목코드
            refresh (str, optional):
                기존등록유지여부(기존유지:'1', 신규등록:'0').
                Defaults to '1'.
        """

        assert len(codes) <= 100, f"Max 100 codes per group, got {len(codes)} codes."
        await self.socket.send(
            {
                "trnm": "REG",
                "grp_no": grp_no,
                "refresh": refresh,
                "data": [
                    {
                        "item": codes,
                        "type": ["0B"],
                    }
                ],
            }
        )

    async def register_hoga(
        self,
        grp_no: str,
        codes: list[str],
        refresh: str = "1",
    ) -> None:
        """
        (실시간시세 > 주식호가잔량 '0D')
        Register order book with given grp_no and codes with refresh option.

        Args:
            grp_no (str): 그룹번호
            codes (list[str]): 종목코드
            refresh (str, optional):
                기존등록유지여부(기존유지:'1', 신규등록:'0').
                Defaults to '1'.
        """

        assert len(codes) <= 100, f"Max 100 codes per group, got {len(codes)} codes."
        await self.socket.send(
            {
                "trnm": "REG",
                "grp_no": grp_no,
                "refresh": refresh,
                "data": [
                    {
                        "item": codes,
                        "type": ["0D"],
                    }
                ],
            }
        )

    async def remove_register(self, grp_no: str, type: str | list[str]) -> None:
        """
        Remove registered group with given grp_no and real tr type.
        if types is empty, nothing is done.

        Args:
            grp_no (str): 그룹번호
            type (str | list[str]): 실시간 데이터 타입 e.g. (0B, 0D, DD)
        """
        if not grp_no or not type:
            return
        if isinstance(type, str):
            type = [type]
        await self.socket.send(
            {"trnm": "REMOVE", "grp_no": grp_no, "refresh": "", "data": [{"type": type}]}
        )
