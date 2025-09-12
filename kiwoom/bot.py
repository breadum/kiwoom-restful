import asyncio

from pandas import DataFrame

from kiwoom import proc
from kiwoom.api import API


class Bot:
    """
    The highest level of usage for Kiwoom REST API
    """

    def __init__(self, host: str, appkey: str, secretkey: str):
        """
        Initialize the bot class.

        Args:
            host (str): domain of Kiwoom REST API
            appkey (str): file path or raw appkey
            secretkey (str): file path or raw secretkey
        """
        self.api = API(host, appkey, secretkey)

    def debug(self, debugging: bool = True) -> None:
        """
        Set debugging mode that will print every request and response.

        Args:
            debugging (bool): debugging mode is False at first
        """
        self.api.debugging = debugging

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def token(self) -> str:
        """
        Returns:
            str: token
        """
        return self.api.token()

    async def connect(self):
        """
        Connect to Kiwoom REST API server.
        """
        await self.api.connect()
        await asyncio.sleep(1)

    async def close(self):
        """
        Close the connection and clean up resources.
        """
        await self.api.close()

    async def stock_list(self, market: str, ats: bool = True) -> list[str]:
        """
        Get stock list for given market.

        Args:
            market (str): {
                'KOSPI': '0',
                'KOSDAQ': '10',
                'ELW': '3',
                '뮤추얼펀드': '4',
                '신주인수권': '5',
                '리츠': '6',
                'ETF': '8',
                '하이일드펀드': '9',
                'K-OTC': '30',
                'KONEX': '50',
                'ETN': '60',
                'NXT': 'NXT'
            }
            ats (bool, optional): 대체거래소 반영한 통합코드 여부. Defaults to True.

        Returns:
            list[str]: stock codes
        """
        # Add NXT market
        if market == "NXT":
            kospi = await self.stock_list("0")
            kosdaq = await self.stock_list("10")
            codes = [c for c in kospi + kosdaq if "AL" in c]
            return sorted(codes)

        data = await self.api.stock_list(market)
        codes = proc.stock_list(data, ats)
        return codes

    async def candle(
        self,
        code: str,
        period: str,
        ctype: str,
        start: str = None,
        end: str = None,
    ) -> DataFrame:
        """
        Get candle chart data for given code, period, and code type.

        Args:
            code (str): code of stock or sector, e.g. '005930_AL'
            period (str): period of candle, {"tick", "min", "day"}
            ctype (str): type of stock or sector, {"stock", "sector"}
            start (str, optional): start date in YYYYMMDD format. Defaults to None.
            end (str, optional): end date in YYYYMMDD format. Defaults to None.

        Returns:
            DataFrame: _description_
        """
        data = await self.api.candle(code, period, ctype, start, end)
        df = proc.candle.process(data, code, period, ctype, start, end)
        return df

    async def trade(self, start: str, end: str = "") -> DataFrame:
        """
        계좌 체결내역 (키움증권 0343 화면)
        Get trade data for given start and end date.

        Args:
            start (str): start date in YYYYMMDD format.
            end (str, optional): end date in YYYYMMDD format. Defaults to "".

        Returns:
            DataFrame: 키움증권 0343 화면 체결내역 Excel 형식
        """
        data = await self.api.trade(start, end)
        df = proc.trade.process(data)
        return df

    async def run(self):
        """
        Run the bot with strategy logic.
        """
        pass
