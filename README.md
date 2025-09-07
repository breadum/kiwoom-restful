Kiwoom REST API
* HTTP Request & Response are handled
  
Basic Structure
* HTTP Client : HTTP 요청과 응답 관리
* API : 키움 API 사용을 위한 입출력 관리
* Proc : 서버에서 받는 Raw 데이터 가공 
* Bot : 실질적인 사용을 위한 Class


```
import asyncio
from datetime import datetime, timedelta
from kiwoom import Bot, REAL
from kiwoom.proc import candle, trade

# 초기화
bot = Bot(
    host=REAL,
    appkey='path/to/appkey',  # or raw appkey
    secretkey='path/to/secretkey'  # or raw secretkey
)

# 거래소 종목코드
kospi, kosdaq = '0', '10'
codes = asyncio.run(bot.stock_list(kospi, ats=True))

# 분봉 데이터
code = '005930_AL'  # 거래소 통합코드
df = asyncio.run(
    bot.candle(
        code=code, 
        period='min',   # 'tick' | 'min' | 'day'
        ctype='stock',  # 'stock' | 'sector'
        start='20250801',
        end='',
))
asyncio.run(candle.to_csv(file=code, path='./', df))

# 계좌 체결내역 데이터 (최근 2달만)
fmt = '%Y%m%d'
today = datetime.today()
start = today - timedelta(days=60)
start = start.strftime(fmt)
end = end.strftime(fmt)

trs = asyncio.run(
    bot.trade(start, end)
)
asyncio.run(trade.to_csv('trade.csv', './', trs))
