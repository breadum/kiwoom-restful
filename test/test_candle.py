import asyncio
import time
from datetime import datetime, timedelta

import pandas as pd

from kiwoom import REAL, Bot
from kiwoom.proc.candle import to_csv


def timer(fn):
    async def timer(*args, **kwargs):
        start = time.time()
        res = await fn(*args, **kwargs)
        elapsed = time.time() - start
        print(fn.__name__, f"{elapsed:.2f} sec", "\n")
        return res

    return timer


@timer
async def test_stock_tick(bot):
    code = "005930_AL"
    start = datetime.today() - pd.tseries.offsets.BDay(1)
    start = start.strftime("%Y%m%d")
    end = start

    print(f"Tick({code=}, {start=}, {end=})")
    df = await bot.candle(code, "tick", "stock", start=start, end=end)
    print(df)
    return df


@timer
async def test_stock_min(bot):
    code = "005930_AL"
    start = datetime.today() - timedelta(days=4)
    end = start + timedelta(days=1)
    start = start.strftime("%Y%m%d")
    end = end.strftime("%Y%m%d")

    print(f"Min({code=}, {start=}, {end=})")
    df = await bot.candle(code, "min", "stock", start=start, end=end)
    print(df)
    return df


@timer
async def test_stock_day(api):
    code = "005930_AL"
    start = datetime.today() - timedelta(days=5)
    end = start + timedelta(days=1)
    start = start.strftime("%Y%m%d")
    end = end.strftime("%Y%m%d")

    print(f"Day({code=}, {start=}, {end=})")
    df = await api.candle(code, "day", "stock", start=start, end=end)
    print(df)
    return df


@timer
async def test_sector_tick(api):
    code = "001"
    start = datetime.today() - pd.tseries.offsets.BDay(1)
    start = start.strftime("%Y%m%d")
    end = start

    print(f"Tick({code=}, {start=}, {end=})")
    df = await api.candle(code, "tick", "sector", start=start, end=end)
    print(df)
    return df


@timer
async def test_sector_min(api):
    code = "001"
    start = datetime.today() - timedelta(days=4)
    end = start + timedelta(days=1)
    start = start.strftime("%Y%m%d")
    end = end.strftime("%Y%m%d")

    print(f"Min({code=}, {start=}, {end=})")
    df = await api.candle(code, "min", "sector", start=start, end=end)
    print(df)
    return df


@timer
async def test_sector_day(bot):
    code = "001"
    start = datetime.today() - timedelta(days=5)
    end = start + timedelta(days=1)
    start = start.strftime("%Y%m%d")
    end = end.strftime("%Y%m%d")

    print(f"Day({code=}, {start=}, {end=})")
    df = await bot.candle(code, "day", "sector", start=start, end=end)
    print(df)
    return df


@timer
async def test_to_csv(bot):
    code = "005930_AL"
    start = datetime.today() - timedelta(days=3)
    start = start.strftime("%Y%m%d")
    end = start

    print(f"Min({code=}, {start=}, {end=})")
    df = await bot.candle(code, "min", "stock", start=start, end=end)
    print(f"Save('./{code}.csv'")
    await to_csv(code, ".", df)
    print(df)
    return df


async def main():
    appkey = "../keys/appkey.txt"
    scretkey = "../keys/secretkey.txt"
    async with Bot(REAL, appkey, scretkey) as bot:
        await bot.connect()
        bot.debug(False)

        # Stock
        await test_stock_tick(bot)
        await test_stock_min(bot)
        await test_stock_day(bot)

        # Sector
        await test_sector_tick(bot)
        await test_sector_min(bot)
        await test_sector_day(bot)

        # Save
        await test_to_csv(bot)


if __name__ == "__main__":
    df = asyncio.run(main())
