import time
import asyncio
import pandas as pd

from datetime import datetime, timedelta
from kiwoom import Bot, REAL
from kiwoom.config.trade import REQUEST_LIMIT_DAYS
from kiwoom.proc.trade import to_csv


def test_trade(bot):
    fmt = '%Y%m%d'
    today = datetime.today()
    start = today - timedelta(days=REQUEST_LIMIT_DAYS)
    start, end = start.strftime(fmt), today.strftime(fmt)

    print(f'Trade({start=}, {end=})')
    df = asyncio.run(bot.trade(start, end))
    print(df)
    return df


def test_to_csv(df):
    print(f"Save('./trade.csv')")
    asyncio.run(to_csv('trade.csv', '.', df, encoding='euc-kr'))
    return df


if __name__ == '__main__':
    appkey = '../keys/appkey.txt'
    scretkey = '../keys/secretkey.txt'
    bot = Bot(REAL, appkey, scretkey)
    bot.api.debugging = False

    trades = test_trade(bot)
    trades = test_to_csv(trades)
