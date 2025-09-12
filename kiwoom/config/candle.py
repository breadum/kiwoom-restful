import pandas as pd

PERIOD_TO_API_ID: dict[str, dict[str, str]] = {
    "stock": {"tick": "ka10079", "min": "ka10080", "day": "ka10081"},
    "sector": {"tick": "ka20004", "min": "ka20005", "day": "ka20006"},
}

PERIOD_TO_DATA: dict[str, dict[str, str]] = {
    "stock": {
        "tick": {"stk_cd": "", "tic_scope": "1", "upd_stkpc_tp": "1"},
        "min": {"stk_cd": "", "tic_scope": "1", "upd_stkpc_tp": "1"},
        "day": {"stk_cd": "", "base_dt": "", "upd_stkpc_tp": "1"},
    },
    "sector": {
        "tick": {"inds_cd": "", "tic_scope": "1"},
        "min": {"inds_cd": "", "tic_scope": "1"},
        "day": {"inds_cd": "", "base_dt": ""},
    },
}

PERIOD_TO_TIME_KEY: dict[str, str] = {"tick": "cntr_tm", "min": "cntr_tm", "day": "dt"}

PERIOD_TO_TIME_FORMAT: dict[str, str] = {
    "tick": "%Y%m%d%H%M%S",
    "min": "%Y%m%d%H%M%S",
    "day": "%Y%m%d",
}

PERIOD_TO_BODY_KEY: dict[str, dict[str, str]] = {
    "stock": {
        "tick": "stk_tic_chart_qry",
        "min": "stk_min_pole_chart_qry",
        "day": "stk_dt_pole_chart_qry",
    },
    "sector": {"tick": "inds_tic_chart_qry", "min": "inds_min_pole_qry", "day": "inds_dt_pole_qry"},
}

PERIOD_TO_COLUMN: dict[str, list[str]] = {
    "tick": ["체결시간", "체결가", "거래량"],
    "min": ["체결시간", "시가", "고가", "저가", "종가", "거래량"],
    "day": ["일자", "시가", "고가", "저가", "종가", "거래량", "거래대금"],
}

COLUMN_MAPPER_CANDLE: dict[str, dict[str, str]] = {
    "tick": {
        "cntr_tm": "체결시간",
        "cur_prc": "체결가",
        "trde_qty": "거래량",
    },
    "min": {
        "cntr_tm": "체결시간",
        "open_pric": "시가",
        "high_pric": "고가",
        "low_pric": "저가",
        "cur_prc": "종가",
        "trde_qty": "거래량",
    },
    "day": {
        "dt": "일자",
        "open_pric": "시가",
        "high_pric": "고가",
        "low_pric": "저가",
        "cur_prc": "종가",
        "trde_qty": "거래량",
        "trde_prica": "거래대금",
    },
}

# 예외적인 체결시간 케이스 변환기 (in Regular Expression)
_DATETIME_REPLACER: dict[str, str] = {
    "888888$": "160000",  # 장마감 시간에 이루어진 거래 (16:00:00)
    "999999$": "180000",  # 시간외 종료에 이루어진 거래 (18:00:00)
}

# 예외적인 코드의 예외적인 체결시간 케이스 변환기
_EXCEPTIONAL_DATETIME_REPLACER: dict[str, dict[str, str]] = {
    "253": {  # K200 F 매수 콜매도
        "888888$": "170000",
        "999999$": "180000",
    },
    "254": {  # K200 F 매도 풋매도
        "888888$": "170000",
        "999999$": "180000",
    },
}

# 장 시작시간이 변경된 예외
DELAYED_MARKET_OPENING: dict[str, int] = {
    # 'YYYYMMDD': delay(hour)
    "20201203": 1,  # 수능일 1시간 지연
    "20211118": 1,  # 수능일 1시간 지연
    "20221117": 1,  # 수능일 1시간 지연
    "20231116": 1,  # 수능일 1시간 지연
    "20241114": 1,  # 수능일 1시간 지연
    "20251113": 1,  # 수능일 1시간 지연
}


# Handle 예외적인 체결시간 (888888, 999999)
def handle_time(df, code: str, period: str) -> pd.DataFrame:
    # If not sector, not much to handle
    col = PERIOD_TO_COLUMN[period][0]  # column name of time
    fmt = PERIOD_TO_TIME_FORMAT[period]  # column time format
    if not (len(code) == 3) or col != "체결시간":
        df[col] = pd.to_datetime(df[col], format=fmt)
        return df

    # To choose exceptional datetime replacer
    replacer = _DATETIME_REPLACER
    if code in _EXCEPTIONAL_DATETIME_REPLACER:
        replacer = _EXCEPTIONAL_DATETIME_REPLACER[code]

    # To handle delayed market openings (ex. 수능일)
    date = lambda s: pd.Timestamp(s).date()
    start = date(df[col].iat[0][: len("YYYYMMDD")])
    end = date(df[col].iat[-1][: len("YYYYMMDD")])
    delayed: dict[int, pd.Timestamp] = dict()
    for ymd, hour in DELAYED_MARKET_OPENING.items():
        if start <= date(ymd) <= end:
            # Add delayed hours to replacer
            delayed_replacer = dict(replacer)
            for regex, hhmmss in delayed_replacer.items():
                hhmmss = min(int(hhmmss) + (hour * 10000), 180000)
                hhmmss = str(hhmmss).zfill(6)
                delayed_replacer[regex] = hhmmss

            # Apply delayed replacer to corresponding items
            for regex, hhmmss in delayed_replacer.items():
                data = df.loc[df[col].str.match(ymd), col]
                target = data.loc[data.str.contains(regex, regex=True)]
                target = target.replace(regex={regex: hhmmss})
                for idx, tsp in target.items():
                    delayed[idx] = pd.to_datetime(tsp, format=fmt)

    # Apply normal replacer at first
    df[col] = df[col].replace(regex=replacer)
    # To make column as pandas datetime series
    df[col] = pd.to_datetime(df[col], format=fmt)
    # Replace delayed items
    df.loc[list(delayed.keys()), col] = list(delayed.values())
    # Return dataframe with column in datetime series
    return df


def valid(body: dict, period: str, ctype: str) -> bool:
    key: str = PERIOD_TO_BODY_KEY[ctype][period]
    empty: bool = not body[key]
    dummy: bool = (len(body[key]) == 1) and (not body[key][0]["cur_prc"])
    return not (empty or dummy)
