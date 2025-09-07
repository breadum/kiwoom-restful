import asyncio
import pandas as pd

from datetime import datetime, timedelta

from kiwoom.http.client import Client
from kiwoom.config import REQ_LIMIT_TIME
from kiwoom.config.candle import *
from kiwoom.config.trade import *


class API(Client):
    """
    Request and Receive data with Kiwoom REST API
    """
    def __init__(self, host: str, appkey: str, secretkey: str):
        super().__init__(host, appkey, secretkey)

    async def stock_list(self, market: str):
        """
        market:
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
        """
        endpoint = '/api/dostk/stkinfo'
        api_id = 'ka10099'

        await asyncio.sleep(REQ_LIMIT_TIME)
        res = await self.request(endpoint, api_id, data={'mrkt_tp': market})
        body = res.json()
        if not body['list'] or len(body['list']) <= 1:
            raise ValueError(
                f'Stock list is not available for market code, {market}.'
            )
        return body

    async def candle(
        self, 
        code: str, 
        period: str, 
        ctype: str, 
        start: str = None, 
        end: str = None, 
    ) -> dict:

        endpoint = '/api/dostk/chart'
        api_id = PERIOD_TO_API_ID[ctype][period]
        data = dict(PERIOD_TO_DATA[ctype][period])
        match ctype:
            case 'stock':
                data['stk_cd'] = code
            case 'sector':
                data['inds_cd'] = code
            case _:
                raise ValueError(
                    f"'ctype' must be one of [stock, sector], not {ctype=}."
                )
        if period == 'day':
            end = end if end else datetime.now().strftime('%Y%m%d')
            data['base_dt'] = end

        ymd: int = len('YYYYMMDD')  # 8 digit compare
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

        body = await self.request_until(
            should_continue, 
            endpoint, 
            api_id, 
            data=data
        )
        return body

    async def trade(self, start: str, end: str = '') -> list[dict]:
        endpoint = '/api/dostk/acnt'
        api_id = 'kt00009'
        data = {
            'ord_dt': '',  # YYYYMMDD (Optional)
            'qry_tp': '1',  # 전체/체결
            'stk_bond_tp': '1',  # 전체/주식/채권
            'mrkt_tp': '0',  # 전체/코스피/코스닥/OTCBB/ECN
            'sell_tp': '0',  # 전체/매도/매수
            'dmst_stex_tp': '%',  # 전체/KRX/NXT/SOR
            # 'stk_cd': '',  # 종목코드 (Optional)
            # 'fr_ord_no': '',  # 시작주문번호 (Optional)
        }
    
        today = datetime.today()
        start = datetime.strptime(start, '%Y%m%d')
        start = max(start, today-timedelta(days=REQUEST_LIMIT_DAYS))
        end = datetime.strptime(end, '%Y%m%d') if end else datetime.today()
        end = min(end, datetime.today())

        trs = []
        key = 'acnt_ord_cntr_prst_array'
        for bday in pd.bdate_range(start, end):
            dic = dict(data)
            dic['ord_dt'] = bday.strftime('%Y%m%d')
            body = await self.request_until(lambda x: True, endpoint, api_id, data=dic)
            if key in body:
                # Append order date to each record
                for rec in body[key]:
                    rec['ord_dt'] = bday.strftime('%Y-%m-%d')
                trs.extend(body[key])
        return trs
