 Kiwoom REST API
* 토큰 만료시 필요에 의해 자동 재발급  


```
import asyncio
from kiwoom import Kiwoom, REAL
from kiwoom.config import candle

bot = Kiwoom(
    host=REAL,
    appkey='path/to/appkey',  # or raw appkey
    secretkey='path/to/secretkey'  # or raw secretkey
)

# Download
code = '005930_AL'  # 거래소 통합코드
df = asyncio.run(
    bot.candle(
        code=code, 
        period='min',   # 'tick' | 'min' | 'day'
        ctype='stock',  # 'stock' | 'sector'
        start='20250801',
        end='',
))
# Save
asyncio.run(candle.to_csv(file=code, path='.', df))
```
