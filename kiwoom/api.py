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
from kiwoom.config.http import WEBSOCKET_QUEUE_MAX_SIZE, State
from kiwoom.config.real import RealData, RealType
from kiwoom.config.trade import (
    REQUEST_LIMIT_DAYS,
)
from kiwoom.http.client import Client
from kiwoom.http.socket import Socket
from kiwoom.http.utils import (
    cancel,
    wrap_async_callback,
    wrap_sync_callback,
)


class API(Client):
    """
    Kiwoom REST API 서버와 직접 요청과 응답을 주고받는 클래스입니다.

    데이터 조회, 주문 요청 등 저수준 통신을 담당하며,
    직접 API 스펙을 구현하여 활용합니다.
    """

    def __init__(self, host: str, appkey: str, secretkey: str):
        """
        API 클래스 인스턴스를 초기화합니다.

        Args:
            host (str): 실서버 / 모의서버 도메인
            appkey (str): 파일경로 / 앱키
            secretkey (str): 파일경로 / 시크릿키

        Raises:
            ValueError: 유효하지 않은 도메인
        """
        match host:
            case config.REAL:
                wss_url = Socket.REAL + Socket.ENDPOINT
            case config.MOCK:
                wss_url = Socket.MOCK + Socket.ENDPOINT
            case _:
                raise ValueError(f"Invalid host: {self.host}")

        super().__init__(host, appkey, secretkey)
        self.queue = asyncio.Queue(maxsize=WEBSOCKET_QUEUE_MAX_SIZE)
        self.socket = Socket(url=wss_url, queue=self.queue)

        self._state = State.CLOSED
        self._state_lock = asyncio.Lock()
        self._recv_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._stop_event.set()

        self._sem = asyncio.Semaphore(config.http.WEBSOCKET_MAX_CONCURRENCY)
        async_print = wrap_sync_callback(self._sem, lambda msg: print(msg))
        self._callbacks = defaultdict(lambda: async_print)
        self._add_default_callback_on_real_data()

    async def connect(self):
        """
        키움 REST API HTTP 서버와 Websocket 서버에 접속하고 토큰을 발급받습니다.

        Raises:
            RuntimeError: 토큰을 발급받지 못한 경우
            Exception: 예상하지 못한 에러
        """
        async with self._state_lock:
            if self._state in (State.CONNECTED, State.CONNECTING):
                return

            self._state = State.CONNECTING
            try:
                # Cancel existing task
                self._stop_event.set()
                await cancel(self._recv_task)

                # Connect http server
                await super().connect(self._appkey, self._secretkey)
                if not (token := self.token()):
                    raise RuntimeError("Not connected: token is not available.")

                # Connect websocket server
                await self.socket.connect(self._session, token)

                # Run websocket receiving task
                self._stop_event.clear()
                self._recv_task = asyncio.create_task(self._on_receive_websocket(), name="dequeue")
                self._state = State.CONNECTED

            except Exception as err:
                self._state = State.CLOSED
                with contextlib.suppress(Exception):
                    await self.socket.close()
                with contextlib.suppress(Exception):
                    await super().close()
                raise Exception from err

    async def close(self):
        """
        키움 REST API 서버와 연결을 해제하고 리소스를 정리합니다.
        """
        async with self._state_lock:
            if self._state in (State.CLOSED, State.CLOSING):
                return

            self._state = State.CLOSING
            try:
                # Cancel existing task
                self._stop_event.set()
                await cancel(self._recv_task)
                self._recv_task = None

                # Close websocket server
                await self.socket.close()
                # Close http server
                await super().close()

            finally:
                self._state = State.CLOSED

    async def stock_list(self, market: str) -> dict:
        """
        주어진 market 코드에 대해 'ka10099' API 요청을 하고 응답을 반환합니다.

        Args:
            market (str): 조회할 주식 시장코드

        Raises:
            ValueError: 종목코드 목록이 없을 경우

        Returns:
            dict: 종목코드 목록을 포함하는 응답
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
        주어진 코드, 기간, 종목/업종 유형에 해당하는 API 요청을 하고 응답을 반환합니다.

        "stock": {"tick": "ka10079", "min": "ka10080", "day": "ka10081"}

        "sector": {"tick": "ka20004", "min": "ka20005", "day": "ka20006"}

        Args:
            code (str): 종목코드 / 업종코드
            period (str): 캔들 기간유형, {"tick", "min", "day"}.
            ctype (str): 종목 / 업종 유형, {"stock", "sector"}.
            start (str, optional): 시작일자 in YYYYMMDD format.
            end (str, optional): 종료일자 in YYYYMMDD format.

        Raises:
            ValueError: 유효하지 않은 'ctype' 또는 'period'

        Returns:
            dict: 캔들 데이터를 포함하는 json 응답
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
        주어진 시작일자와 종료일자에 해당하는 체결내역을
        키움증권 '0343' 계좌 체결내역 화면과 동일한 구성으로 반환합니다.
        데이터 조회 제한으로 최근 2개월 데이터만 조회할 수 있습니다.

        체결내역 데이터는 [알파노트](http://alphanote.io)를 통해
        간편하게 진입/청산 시각화 및 성과 지표들을 확인할 수 있습니다.

        Args:
            start (str): 시작일자 in YYYYMMDD format
            end (str, optional): 종료일자 in YYYYMMDD format

        Returns:
            list[dict]: 체결내역 데이터를 포함하는 json 응답 리스트
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
        실시간 데이터 수신 시 호출될 콜백 함수를 추가합니다. (trnm이 'REAL'인 경우)

        * callback 함수는 서버 응답 string 그대로를 인자로 받습니다.
        * real_type을 'PING' 또는 'LOGIN'으로 설정하면 기본 콜백 함수를 덮어씁니다.

        콜백 함수는 비동기 콜백 함수를 추가하는 것을 권장합니다.
        비동기 및 동기 콜백 함수 모두 루프를 블로킹하지 않도록
        백그라운드에서 실행됩니다. 따라서 데이터 처리 완료 순서가 반드시
        데이터 수신 순서에 따라 실행되지 않을 수 있습니다.

        ex) tick 체결 데이터 (type 'OB')가 수신될 때마다 데이터 출력하기

            > fn = lambda raw: print(raw)

            > add_callback_on_real_data(real_type='OB', callback=fn)

        Args:
            real_type (str): 키움 REST API에 정의된 실시간 데이터 타입
            callback (Callable): raw 스트링을 인자로 받는 콜백 함수
        """

        real_type = real_type.upper()
        # Asnyc Callback
        if iscoroutinefunction(callback):
            self._callbacks[real_type] = wrap_async_callback(self._sem, callback)
        # Sync Callback
        else:
            self._callbacks[real_type] = wrap_sync_callback(self._sem, callback)

    def _add_default_callback_on_real_data(self) -> None:
        """
        Add default callback functions on real data receive.
        """

        # Ping
        async def callback_on_ping(msg: dict):
            await self.socket.send(msg)

        self.add_callback_on_real_data(real_type="PING", callback=callback_on_ping)

        # Login
        def callback_on_login(msg: dict):
            if msg.get("return_code") != 0:
                raise RuntimeError(f"Login failed with return_code not zero, {msg}.")
            print(msg)

        self.add_callback_on_real_data(real_type="LOGIN", callback=callback_on_login)

    async def _on_receive_websocket(self) -> None:
        """
        Receive websocket data and dispatch to the callback function.
        Decoder patially checks 'trnm' and 'type' in order to speed up.

        If trnm is "REAL", the argument to callback function is RealData instance.
        Otherwise, the argument to callback function is json dict.

        Raises:
            Exception: Exception raised by the callback function or decoder
        """
        decoder = msgspec.json.Decoder(type=RealType)
        while not self._stop_event.is_set():
            try:
                raw: str = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                msg = decoder.decode(raw)  # partially decoded for speed up
                if msg.trnm == "REAL":
                    for data in msg.data:
                        asyncio.create_task(
                            self._callbacks[data.type](
                                RealData(bytes(data.values), data.type, data.name, data.item)
                            )
                        )
                    continue

                dic = orjson.loads(raw)
                asyncio.create_task(self._callbacks[msg.trnm](dic))

            except Exception as err:
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
        주어진 그룹번호와 종목 코드에 대해 주식체결 데이터를 등록합니다. (타입 '0B')

        Args:
            grp_no (str): 그룹번호
            codes (list[str]): 종목코드 리스트
            refresh (str, optional): 기존등록유지여부 (기존유지:'1', 신규등록:'0').
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
        주어진 그룹번호와 종목 코드에 대해 주식호가잔량 데이터를 등록합니다. (타입 '0D')

        Args:
            grp_no (str): 그룹번호
            codes (list[str]): 종목코드 리스트
            refresh (str, optional): 기존등록유지여부 (기존유지:'1', 신규등록:'0').
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
        주어진 그룹번호와 실시간 데이터 타입에 대해 등록된 데이터를 제거합니다.

        Args:
            grp_no (str): 그룹번호
            type (str | list[str]): 실시간 데이터 타입 ex) '0B', '0D', 'DD'
        """
        if not grp_no or not type:
            return
        if isinstance(type, str):
            type = [type]
        await self.socket.send(
            {"trnm": "REMOVE", "grp_no": grp_no, "refresh": "", "data": [{"type": type}]}
        )
