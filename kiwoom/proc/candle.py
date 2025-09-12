from os import getcwd, makedirs
from os.path import exists, isdir, join
from pathlib import Path

from pandas import DataFrame

from kiwoom.config import ENCODING
from kiwoom.config.candle import (
    COLUMN_MAPPER_CANDLE,
    PERIOD_TO_BODY_KEY,
    PERIOD_TO_COLUMN,
    handle_time,
    valid,
)


# 캔들차트 관련 처리함수
def process(
    data: dict,
    code: str,
    period: str,
    ctype: str,
    start: str,
    end: str,
) -> DataFrame:
    columns: list[str] = PERIOD_TO_COLUMN[period]
    if not valid(data, period, ctype):
        # Returns empty dataframe
        df = DataFrame(columns=columns)
        return df

    key: str = PERIOD_TO_BODY_KEY[ctype][period]
    df = DataFrame(data[key])
    df = df[::-1]

    mapper = COLUMN_MAPPER_CANDLE[period]
    df.rename(columns=mapper, inplace=True)
    df = df[columns]

    time = columns[0]
    df = handle_time(df, code, period)
    df.set_index(time, drop=True, inplace=True)
    if not df.index.is_monotonic_increasing:
        df = df.sort_index(kind="stable")
    df = df.astype(int).abs()
    df = df.loc[start:end]
    return df


async def to_csv(file: str, path: str, df: DataFrame, encoding: str = ENCODING) -> None:
    # Validate
    if df.empty:
        return
    if not path:
        path = getcwd()
    if not isdir(path):
        raise ValueError(f"Path not valid: '{path}'")
    if not exists(path):
        makedirs(path)

    # Save
    if not file.endswith(".csv"):
        file = f"{file}.csv"
    file = join(path, file)
    if exists(file):
        Path.unlink(file)
    df.to_csv(file, encoding=encoding)
