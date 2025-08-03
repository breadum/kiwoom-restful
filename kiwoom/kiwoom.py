import pandas as pd

from typing import Any
from datetime import datetime

from kiwoom.api import API
from kiwoom.config.candle import *
from kiwoom.config.trade import *


class Kiwoom(API):
    def __init__(self, host: str, appkey: str, secretkey: str):
        super().__init__(host, appkey, secretkey)

    async def stock_list(self, market: str):
        endpoint = '/api/dostk/stkinfo'
        api_id = 'ka10099'
        
        if market.upper() == 'NXT':
            kospi = await self.stock_list('0')
            kosdaq = await self.stock_list('10')
            codes = [c for c in kospi + kosdaq if 'AL' in c]
            return sorted(codes)

        data = {'mrkt_tp': market}
        data = await self.chain_request(None, endpoint, api_id, data=data)
        if not data['list'] or len(data['list']) <= 1:
            raise ValueError(
                f'Stock list is not available for market code, {market}.'
            )
        
        codes = list()
        for dic in data['list']:
            if dic['nxtEnable'] == 'Y':
                codes.append(dic['code'] + '_AL')
                continue
            codes.append(dic['code'])
        codes = sorted(codes)
        return codes

    async def candle(
        self, 
        code: str, 
        period: str, 
        ctype: str, 
        start: str = None, 
        end: str = None, 
    ) :

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
        def cond(body: dict) -> bool:
            # Validate
            if not valid(body, period, ctype):
                return False
            # Full data
            if not start:
                return True
            # Condition to continue
            chart = body[key]
            earliest = chart[-1][time][:ymd]
            return start <= earliest

        columns: list[str] = PERIOD_TO_COLUMN[period]
        data = await self.chain_request(cond, endpoint, api_id, data=data)
        if not valid(data, period, ctype):
            df = pd.DataFrame(columns=columns)
            return df

        mapper = COLUMN_MAPPER_CANDLE[period]
        df = pd.DataFrame(data[key])
        df = df[::-1]
        df.rename(columns=mapper, inplace=True)
        df = df[columns]

        time = columns[0]
        df = handle_time(df, code, period)
        df.set_index(time, drop=True, inplace=True)
        if not df.index.is_monotonic_increasing:
            df = df.sort_index(kind='stable')
        df = df.astype(int).abs()
        df = df.loc[start:end]
        return df

    async def trades(self, start: str, end: str = '') -> pd.DataFrame:
        endpoint = '/api/dostk/acnt'
        api_id = 'kt00009'
        data = {
            # 'ord_dt': '20250801',  # YYYYMMDD (Optional)
            'stk_bond_tp': '1',  # 전체/주식/채권
            'mrkt_tp': '0',  # 전체/코스피/코스닥/OTCBB/ECN
            'sell_tp': '0',  # 전체/매도/매수
            'qry_tp': '1',  # 전체/체결
            # 'stk_cd': '',  # 종목코드 (Optional)
            # 'fr_ord_no': '',  # 시작주문번호 (Optional)
            'dmst_stex_tp': '%',  # 전체/KRX/NXT/SOR
        }
        start = datetime.strptime(start, '%Y%m%d')
        end = datetime.strptime(end, '%Y%m%d') if end else datetime.today()
        end = min(end, datetime.today())

        trs = []
        for bday in pd.bdate_range(start, end):
            dic = dict(data)
            dic['ord_dt'] = bday.strftime('%Y%m%d')
            body = await self.chain_request(None, endpoint, api_id, data=dic)
            if 'acnt_ord_cntr_prst_array' in body:
                for rec in body['acnt_ord_cntr_prst_array']:
                    rec['주문일자'] = bday.strftime('%Y-%m-%d')
                trs.extend(body['acnt_ord_cntr_prst_array'])

        if not trs:
            return pd.DataFrame(columns=COLUMN_TRADE)
        
        df = pd.DataFrame(trs)
        df.rename(columns=COLUMN_MAPPER_TRADE, inplace=True)
        
        ints = [
            '주문번호', '원주문번호', 
            '주문수량', '주문단가', 
            '확인수량', '스톱가', 
            '체결번호', '체결수량', '체결평균단가'
        ]
        for col in ints:
            df[col] = df[col].astype(int)
        df['주식채권'] = df['주식채권'].map({'1': '주식', '2': '채권'})
        df['원주문번호'] = df['원주문번호'].apply(lambda x: '' if x == 0 else str(x))
        df['종목번호'] = df['종목번호'].str[-6:]
        df['체결시간'] = df['체결시간'].str.lstrip('0')
        df = df[COLUMN_TRADE]
        return df
    