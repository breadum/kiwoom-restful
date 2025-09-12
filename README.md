# Kiwoom REST API
Simple Python Wrapper for Kiwoom RESTful API   

## What is it?
* 키움증권에서 제공하는 'REST' API 인터페이스 사용을 위한 간단한 Python Wrapper 모듈
* 네트워크 프로토콜 디테일은 숨기고 투자 전략 로직에 집중할 수 있도록 설계
* 현재 개발 단계는 RC(Release Candidate)로 구조적인 설계 마무리 단계
* 'REST' API가 아닌 기존 PyQt 기반 OCX 방식 API는 [이곳][ocx]을 참조

## Table of Contents
- [Kiwoom REST API](#kiwoom-rest-api)
  - [What is it?](#what-is-it)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Installation](#installation)
  - [Examples](#examples)
  - [Architecture](#architecture)
  - [License](#license)
  - [Disclaimer](#disclaimer)

## Features
* 간결한 API를 통한 빠른 프로토 타입 및 전략 최적화
* Http 요청 및 응답 + Websocket 실시간 데이터 처리
* 실시간 데이터 처리 루프와 비블로킹 콜백
* msgpsec/orjson 기반 실시간 고속 json 파싱
* 초당 Http 연결/호출 제한 자동관리
* Websocket Ping - Pong 자동처리

모듈 관련 상세한 API 문서 페이지는 [이곳][doc]을 참고해 주세요.

## Installation
```bash
# install from pypi
pip install -U kiwoom-restful

# install from git fork/clone
pip install -e ,
```
Requirements
* python 3.11+ recommended (at leaset 3.10+)
* install uvloop is a plus for linux environment
```python
import asyncio, uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
```

## Examples
HTTP 데이터 교환 구현 예시
```python
import asyncio
from kiwoom import Bot
from kiwoom.proc import candle, trade

class MyBot(Bot):
    async def run():
        # 분봉차트 데이터
        code = '005930_AL'  # 거래소 통합코드
        df = await self.candle(
                code=code, 
                period='min',   # 'tick' | 'min' | 'day'
                ctype='stock',  # 'stock' | 'sector'
                start='20250901',
                end='',
        )
        await candle.to_csv(file=f'{code}.csv', path='./', df)

        # 계좌 체결내역 데이터 (최근 2달만)
        fmt = '%Y%m%d'
        today = datetime.today()
        start = today - timedelta(days=60)
        start = start.strftime(fmt)
        end = end.strftime(fmt)
        trs = self.trade(start, end)
        # 키움증권 0343 매매내역 화면 저장
        await trade.to_csv('trade.csv', './', trs)
```

Websocket 실시간 데이터 요청 구현 예시
```python
import asyncio
import orjson
import pandas as pd
from kiwoom import Bot

class MyBot(Bot):
    def __init__(self, host: str, appkey: str, scretkey: str):
        super().__init__(host, appkey, scretkey)
        self.ticks: list[dict[str, str]] = []

    async def on_receive_order_book(raw: str):
        # 호가 데이터 처리 콜백함수 예시
        # msg = json.loads(raw) # slow
        msg = orjson.loads(raw) # fast
        print(
            f"종목코드: {msg['item']}, "
            f"최우선매도호가: {msg['values']['41']}"
            f"최우선매수호가: {msg['values']['51']}"
        )
    
    async def on_receive_tick(raw: str):
        # 체결 데이터 처리 콜백함수 예시
        self.list.append(orjson.loads(raw))
        if len(self.list) >= 100:
            df = pd.DataFrame(self.list)
            print(df)

    async def run():
        # 거래소 통합 종목코드 받아오기 
        kospi, kosdaq = '0', '10'
        kospi_codes = await bot.stock_list(kospi, ats=True)
        kosdaq_codes = await bot.stock_list(kosdaq, ats=True)

        # 호가 데이터 수신 시 콜백 등록
        self.api.add_callback_on_real_data(
            real_type="0D",  # 실시간시세 > 주식호가잔량
            callback=self.on_receive_order_book
        )
        # 체결 데이터 수신 시 콜백 등록
        self.api.add_callback_on_real_data(
            real_tyle="0B",  # 실시간시세 > 주식체결
            callback=self.on_receive_tick
        )

        # 데이터 수신을 위한 서버 요청
        # > 데이터가 수신되면 자동으로 콜백이 호출됨
        # > grp_no(그룹 번호) 별 종목코드(최대 100개) 관리 필요
        codes1 = kospi_codes[:100]  
        await self.api.register_hoga(grp_no='1', codes=codes1)
        await self.api.register_tick(grp_no='1', codes=codes1)
        
        codes2 = kosdaq_codes[:100]
        await self.api.register_hoga(grp_no='2', codes=codes2)

        codes3 = kospi_codes[100:200]
        await self.api.register_tick(grp_no='3', codes=codes1)

        # 데이터 수신 해제
        await self.api.remove_register(grp_no='1', type=['0B', '0D'])  
        await self.api.remove_register(grp_no='2', type='0D')  # 호가 '0D'
        await self.api.remove_register(grp_no='3', type='0B')  # 체결 '0B'
```

실제 운영을 위한 스크립트 예시
```python
import asyncio
from kiwoom import Bot, REAL

async def main():
    # appkey, scretkey 파일 위치 예시
    appkey = "../keys/appkey.txt"
    scretkey = "../keys/secretkey.txt"

    # async with context 사용을 통한 자동 연결 및 리소스 관리
    async with MyBot(host=REAL, appkey, scretkey) as bot:
        bot.debugging = True  # 요청 및 응답 프린트
        await bot.run()

    # context 외부는 자동 연결 해제
    print('Done')

if __name__ == '__main__':
    asyncio.run(main())

```

## Architecture
Layered Roles
* Client : Http 요청 횟수 제한 관리 및 데이터 연속 조회 관리
* Socket : WebSocket 연결 및 수명 관리, 데이터 수신 후 asyncio.Queue에 전달

* API : 
  * 기본적인 REST API Http 요청 및 응답 관리
  * Queue를 소비하며 Ping/Pong, Login 및 데이터 디코딩 수행
  * 실시간 데이터 주제별 스트림/콜백/구독 관리

* Bot : API 기능을 활용하여 전략을 수행하도록 사용자 구현 

## License
[MIT License][mit] © Contributors

## Disclaimer
* 본 프로젝트는 키움증권 공식 프로젝트가 아닙니다.
* 실제 운용 전 모의 테스트 환경에서 충분히 검증 바랍니다.



[ocx]: https://github.com/breadum/kiwoom
[doc]: https://breadum.github.io/kiwoom-restful/latest/
[mit]: https://github.com/breadum/kiwoom-restful?tab=MIT-1-ov-file