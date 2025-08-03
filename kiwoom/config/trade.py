import pandas as pd

from kiwoom.config.config import ENCODING


COLUMN_TRADE: list[str] = [
    # 1st row 
    '주식채권', '주문번호', '원주문번호', '종목번호', '매매구분', 
    '주문유형구분', '주문수량', '주문단가', '확인수량', '체결번호', '스톱가',
    
    # 2nd row 
    '주문일자', '종목명', '접수구분', '신용거래구분', '체결수량', '체결평균단가', 
    '정정/취소', '통신', '예약/반대', '체결시간', '거래소'
]

COLUMN_MAPPER_TRADE: dict[str, str] = {
    # 1st row
    'stk_bond_tp': '주식채권',
    'ord_no': '주문번호',
    'orig_ord_no': '원주문번호',
    'stk_cd': '종목번호',
    'trde_tp': '매매구분',
    'io_tp_nm': '주문유형구분',
    'ord_qty': '주문수량',
    'ord_uv': '주문단가', 
    'cnfm_qty': '확인수량',
    'cntr_no': '체결번호',
    'cond_uv': '스톱가',

    # 2nd row
    # 주문일자 
    'stk_nm': '종목명',
    'acpt_tp': '접수구분',
    'crd_deal_tp': '신용거래구분',
    'cntr_qty': '체결수량',
    'cntr_uv': '체결평균단가',
    'mdfy_cncl_tp': '정정/취소',
    'comm_ord_tp': '통신',
    'rsrv_oppo': '예약/반대',
    'cntr_tm': '체결시간',
    'dmst_stex_tp': '거래소',
}


async def to_csv(fpath: str, df: pd.DataFrame):
    if df.empty:
        return
    
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
    with open(fpath, 'w', encoding=ENCODING) as f:
        # Header
        f.write(','.join(col1) + '\n')
        f.write(','.join(col2) + '\n')

        # Data
        lines = []
        row1 = df[col1]
        row2 = df[col2]
        for (_, r1), (_, r2) in zip(row1.iterrows(), row2.iterrows()):
            lines.append(','.join(r1) + '\n')
            lines.append(','.join(r2) + '\n')
        f.writelines(lines)
