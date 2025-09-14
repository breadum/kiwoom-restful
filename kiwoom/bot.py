import asyncio
import contextlib
from typing import Self

from pandas import DataFrame

from kiwoom import proc
from kiwoom.api import API
from kiwoom.config.http import EXCEPTIONS_TO_SUPPRESS


class Bot:
    """
    Kiwoom REST API를 이용해 전략을 실행하는 최상위 클래스입니다.

    사용자가 API 세부 동작을 알지 못해도 전략 수행에 집중할 수 있도록 합니다.
    """

    def __init__(self, host: str, appkey: str, secretkey: str, api: API | None = None):
        """
        Bot 클래스 인스턴스를 초기화합니다.

        Args:
            host (str): 실서버 / 모의서버 도메인
            appkey (str): 파일경로 / 앱키
            secretkey (str): 파일경로 / 시크릿키
            api (API, optional): API를 별도로 구현했다면 인스턴스 전달가능
        """
        self.api = api if api else API(host, appkey, secretkey)

    async def __aenter__(self) -> Self:
        """
        async with 구문에서 Bot 인스턴스를 반환합니다.

        Returns:
            Bot: self
        """
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        async with 구문을 종료할 때 연결을 해제하고 리소스를 정리합니다.

        Args:
            exc_type (_type_): exception type
            exc_value (_type_): exception value
            traceback (_type_): traceback
        """
        with contextlib.suppress(EXCEPTIONS_TO_SUPPRESS):
            await asyncio.shield(self.close())

    def debug(self, debugging: bool = True) -> None:
        """
        디버깅 모드 활성화 / 비활성화.
        디버깅 모드에서는 Http 요청과 응답이 출력됩니다.

        Args:
            debugging (bool): 디버깅 모드 활성화 여부
        """
        self.api.debugging = debugging

    def token(self) -> str:
        """
        연결이 되었다면, 키움 REST API 토큰을 반환합니다.

        Returns:
            str: token
        """
        return self.api.token()

    async def connect(self):
        """
        키움 REST API HTTP 서버 및 Websocket 서버에 접속합니다.
        """
        await self.api.connect()
        await asyncio.sleep(1)

    async def close(self):
        """
        키움 REST API HTTP 서버 및 Websocket 서버 연결을 해제합니다.
        """
        await asyncio.shield(self.api.close())

    async def stock_list(self, market: str, ats: bool = True) -> list[str]:
        """
        주어진 market 코드에 해당하는 주식 종목코드 목록을 반환합니다.

        Args:
            market (str): {
                'KOSPI': '0', 'KOSDAQ': '10', 'ELW': '3',
                '뮤추얼펀드': '4', '신주인수권': '5', '리츠': '6',
                'ETF': '8', '하이일드펀드': '9', 'K-OTC': '30',
                'KONEX': '50', 'ETN': '60', 'NXT': 'NXT'}
            ats (bool, optional): 대체거래소 반영한 통합코드 여부 (ex. '005930_AL')

        Returns:
            list[str]: 종목코드 리스트
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

    async def sector_list(self, market: str) -> list[str]:
        """
        주어진 market 코드에 해당하는 업종코드 목록을 반환합니다.

        Args:
            market (str): {
                '0': 'KOSPI', '1': 'KOSDAQ',
                '2': 'KOSPI200', '4': 'KOSPI100(150)',
                '7': 'KRX100'}

        Returns:
            list[str]: 업종코드 리스트
        """
        data = await self.api.sector_list(market)
        codes = proc.sector_list(data)
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
        주어진 코드, 기간, 종목/업종 유형에 해당하는 캔들차트 데이터를 반환합니다.

        Args:
            code (str): 종목코드 / 업종코드
            period (str): 캔들 기간유형 {"tick", "min", "day"}
            ctype (str): 종목 / 업종유형 {"stock", "sector"}
            start (str, optional): 시작일자 in YYYYMMDD format
            end (str, optional): 종료일자 in YYYYMMDD format

        Returns:
            DataFrame: Pandas 캔들차트 데이터프레임
        """
        data = await self.api.candle(code, period, ctype, start, end)
        df = proc.candle.process(data, code, period, ctype, start, end)
        return df

    async def trade(self, start: str, end: str = "") -> DataFrame:
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
            DataFrame: 키움증권 '0343' 화면 'Excel 내보내기' 형식
        """
        data = await self.api.trade(start, end)
        df = proc.trade.process(data)
        return df

    async def run(self):
        """
        전략 로직을 구현하고 실행합니다.
        """
        pass
