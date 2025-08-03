from datetime import timezone, timedelta


REAL = 'https://api.kiwoom.com'
MOCK = 'https://mockapi.kiwoom.com'
WEBSOCKET_ENDPOINT = '/api/dostk/websocket'

STATUS_CODE = {
    200: 'OK',
    400: 'Bad Request',
    404: 'Not Found',
    500: 'Internal Server Error'
}

# API 호출 횟수 제한 정책은 다음 각 호와 같다.
# 1. 조회횟수 초당 5건
# 2. 주문횟수 초당 5건
# 3. 실시간 조건검색 개수 로그인 1개당 10건
REQ_LIMIT_TIME: float = 0.21  # sec

# Time
KST: timezone = timezone(timedelta(hours=9))

# Encoding
ENCODING = 'euc-kr'
