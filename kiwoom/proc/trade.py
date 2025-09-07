from os import getcwd, makedirs
from os.path import isdir, exists, join
from pathlib import Path

from pandas import DataFrame

from kiwoom.config import ENCODING
from kiwoom.config.trade import *


# 체결내역 관련 처리함수
def process(data: list[dict]) -> DataFrame:
    if not data:
        return DataFrame(columns=COLUMN_TRADE)
    
    df = DataFrame(data)
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


async def to_csv(file: str, path: str, df: DataFrame, encoding: str = ENCODING):
    # Validate
    if df.empty:
        print('DataFrame is empty, skip writing to csv.')
        return
    if not path:
        path = getcwd()
    if not isdir(path):
        raise ValueError(f"Path not valid: '{path}'")
    if not exists(path):
        makedirs(path)

    # Save
    if not file.endswith('.csv'):
        file = f'{file}.csv'
    file = join(path, file)
    if exists(file):
        Path.unlink(file)

    # 키움증권 0343 화면 
    col1 = [  # 1st row 
        '주식채권', '주문번호', '원주문번호', '종목번호', '매매구분', 
        '주문유형구분', '주문수량', '주문단가', '확인수량', '체결번호', '스톱가'
    ]
    col2 = [  # 2nd row 
        '주문일자', '종목명', '접수구분', '신용거래구분', '체결수량', '체결평균단가', 
        '정정/취소', '통신', '예약/반대', '체결시간', '거래소'
    ]  
    df = df.astype(str)
    with open(file, 'w', encoding=encoding) as f:
        lines = []
        row1 = df[col1]
        row2 = df[col2]
        for (_, r1), (_, r2) in zip(row1.iterrows(), row2.iterrows()):
            lines.append(','.join(r1) + '\n')
            lines.append(','.join(r2) + '\n')
        
        f.write(','.join(col1) + '\n')  # Header col 1
        f.write(','.join(col2) + '\n')  # Header col 2
        f.writelines(lines)
