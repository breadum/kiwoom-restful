import pandas as pd

from kiwoom import proc as Proc
from kiwoom.api import API


class Bot:
    """
    Highest level API for Kiwoom REST API
    """
    def __init__(self, host: str, appkey: str, secretkey: str):
        self.api = API(host, appkey, secretkey)

    async def stock_list(self, market: str, ats: bool = True) -> list[str]:
        """
        market: str = {
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
        ats: bool = 대체거래소 반영한 통합코드 여부
        """
        # Add NXT market
        if market == 'NXT':
            kospi = await self.stock_list('0')
            kosdaq = await self.stock_list('10')
            codes = [c for c in kospi + kosdaq if 'AL' in c]
            return sorted(codes)

        data = await self.api.stock_list(market)
        codes = Proc.stock_list(data, ats)
        return codes

    async def candle(
        self, 
        code: str, 
        period: str, 
        ctype: str, 
        start: str = None, 
        end: str = None, 
    ) -> pd.DataFrame:
        data = await self.api.candle(code, period, ctype, start, end)
        df = Proc.candle.process(data, code, period, ctype, start, end)
        return df

    async def trade(self, start: str, end: str = '') -> pd.DataFrame:
        data = await self.api.trade(start, end)
        df = Proc.trade.process(data)
        return df

    async def live(self, code: str):
        pass