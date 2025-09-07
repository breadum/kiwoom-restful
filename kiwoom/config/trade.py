REQUEST_LIMIT_DAYS = 60 + 5  # 2 months + extra days

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
    'ord_dt': '주문일자',
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
