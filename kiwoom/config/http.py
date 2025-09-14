import asyncio
from enum import Enum, auto

__all__ = [
    "REQ_LIMIT_TIME",
    "REQ_LIMIT_PER_SECOND",
    "HTTP_TOTAL_TIMEOUT",
    "HTTP_CONNECT_TIMEOUT",
    "HTTP_READ_TIMEOUT",
    "HTTP_TCP_CONNECTORS",
    "WEBSOCKET_HEARTBEAT",
    "WEBSOCKET_MAX_CONCURRENCY",
    "State",
]

# Kiwoom REST API Request Limit Policy
#   API 호출 횟수 제한 정책은 다음 각 호와 같다.
#       1. 조회횟수 초당 5건
#       2. 주문횟수 초당 5건
#       3. 실시간 조건검색 개수 로그인 1개당 10건
REQ_LIMIT_TIME: float = 0.205  # sec
REQ_LIMIT_PER_SECOND: int = 5

# Client & Socket Connection Settings
HTTP_TOTAL_TIMEOUT: float = 10.0
HTTP_CONNECT_TIMEOUT: float = 3.0
HTTP_READ_TIMEOUT: float = 5.0
HTTP_TCP_CONNECTORS: int = 100

WEBSOCKET_HEARTBEAT: int = 30
WEBSOCKET_MAX_CONCURRENCY: int = 1000
WEBSOCKET_QUEUE_MAX_SIZE: int = 0  # no limit


# Connection State
class State(Enum):
    """
    Connection State
    """

    CONNECTING = auto()
    CONNECTED = auto()
    CLOSING = auto()
    CLOSED = auto()


# Http Response Status Code
STATUS_CODE = {200: "OK", 400: "Bad Request", 404: "Not Found", 500: "Internal Server Error"}

# Suppress exceptions to close gracefully
EXCEPTIONS_TO_SUPPRESS = (asyncio.CancelledError, KeyboardInterrupt, Exception)
