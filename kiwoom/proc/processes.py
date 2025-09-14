# 일반적인 처리함수
def stock_list(data: dict, ats: bool = True) -> list[str]:
    codes = list()
    if not ats:
        for dic in data["list"]:
            codes.append(dic["code"])
        codes = sorted(codes)
        return codes

    # 대체거래소 통합시세 코드
    for dic in data["list"]:
        if dic["nxtEnable"] == "Y":
            codes.append(dic["code"] + "_AL")
            continue
        codes.append(dic["code"])
    codes = sorted(codes)
    return codes


def sector_list(data: dict) -> list[str]:
    codes = list()
    for dic in data["list"]:
        codes.append(dic["code"])
    codes = sorted(codes)
    return codes
