import time
import asyncio
import pandas as pd

from datetime import datetime, timedelta
from kiwoom import Kiwoom, REAL
from kiwoom.config.candle import to_csv


def timer(fn):
    def timer(*args, **kwargs):
        start = time.time()
        res = fn(*args, **kwargs)
        elapsed = time.time() - start
        print(fn.__name__, f'{elapsed:.2f} sec', '\n')
        return res
    return timer


@timer
def test_stock_tick(api):
    code = '005930_AL'
    start = datetime.today() - pd.tseries.offsets.BDay(1)
    start = start.strftime('%Y%m%d')
    end = start
    
    print(f'Tick({code=}, {start=}, {end=})')
    df = asyncio.run(api.candle(code, 'tick', 'stock', start=start, end=end))
    print(df)
    return df


@timer
def test_stock_min(api):
    code = '005930_AL'
    start = datetime.today() - timedelta(days=4)
    end = start + timedelta(days=1)
    start = start.strftime('%Y%m%d')
    end = end.strftime('%Y%m%d')

    print(f'Min({code=}, {start=}, {end=})')
    df = asyncio.run(api.candle(code, 'min', 'stock', start=start, end=end))
    print(df)
    return df


@timer
def test_stock_day(api):
    code = '005930_AL'
    start = datetime.today() - timedelta(days=5)
    end = start + timedelta(days=1)
    start = start.strftime('%Y%m%d')
    end = end.strftime('%Y%m%d')

    print(f'Day({code=}, {start=}, {end=})')
    df = asyncio.run(api.candle(code, 'day', 'stock', start=start, end=end))
    print(df)
    return df


@timer
def test_sector_tick(api):
    code = '001'
    start = datetime.today() - pd.tseries.offsets.BDay(1)
    start = start.strftime('%Y%m%d')
    end = start
    
    print(f'Tick({code=}, {start=}, {end=})')
    df = asyncio.run(api.candle(code, 'tick', 'sector', start=start, end=end))
    print(df)
    return df


@timer
def test_sector_min(api):
    code = '001'
    start = datetime.today() - timedelta(days=4)
    end = start + timedelta(days=1)
    start = start.strftime('%Y%m%d')
    end = end.strftime('%Y%m%d')

    print(f'Min({code=}, {start=}, {end=})')
    df = asyncio.run(api.candle(code, 'min', 'sector', start=start, end=end))
    print(df)
    return df


@timer
def test_sector_day(api):
    code = '001'
    start = datetime.today() - timedelta(days=5)
    end = start + timedelta(days=1)
    start = start.strftime('%Y%m%d')
    end = end.strftime('%Y%m%d')

    print(f'Day({code=}, {start=}, {end=})')
    df = asyncio.run(api.candle(code, 'day', 'sector', start=start, end=end))
    print(df)
    return df


@timer
def test_to_csv(api):
    code = '005930_AL'
    start = datetime.today() - timedelta(days=3)
    start = start.strftime('%Y%m%d')
    end = start
    
    print(f'Min({code=}, {start=}, {end=})')
    df = asyncio.run(api.candle(code, 'min', 'stock', start=start, end=end))
    print(f"Save('./{code}.csv'")
    asyncio.run(to_csv(code, '.', df))
    print(df)
    return df


if __name__ == '__main__':
    appkey = '../keys/appkey.txt'
    scretkey = '../keys/secretkey.txt'
    bot = Kiwoom(REAL, appkey, scretkey)
    bot.debugging = False

    # Stock
    tick = test_stock_tick(bot)
    min_ = test_stock_min(bot)
    day = test_stock_day(bot)

    # Sector
    tick = test_sector_tick(bot)
    min_ = test_sector_min(bot)
    day = test_sector_day(bot)

    # Save
    df = test_to_csv(bot)
