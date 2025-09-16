import asyncio
from datetime import datetime, timedelta

from pandas import DataFrame

from kiwoom import REAL, Bot
from kiwoom.config.trade import REQUEST_LIMIT_DAYS
from kiwoom.proc.trade import to_csv


async def test_trade(bot) -> DataFrame:
    # 체결내역 (최근 2달 제한)
    fmt = "%Y%m%d"
    today = datetime.today()
    start = today - timedelta(days=REQUEST_LIMIT_DAYS)
    start, end = start.strftime(fmt), today.strftime(fmt)

    print(f"Trade({start=}, {end=})")
    df = await bot.trade(start, end)
    print(df)
    return df


async def test_to_csv(df: DataFrame):
    print("Save('./trade.csv')")
    await to_csv("trade.csv", ".", df, encoding="euc-kr")
    return df


async def main():
    appkey = "../keys/appkey.txt"
    scretkey = "../keys/secretkey.txt"

    async with Bot(REAL, appkey, scretkey) as bot:
        bot.debug(True)
        await bot.connect()
        df = await test_trade(bot)
        await test_to_csv(df)


if __name__ == "__main__":
    asyncio.run(main())
