import asyncio
import contextlib

import orjson
from aiohttp import ClientSession, ClientWebSocketResponse, WSMessageTypeError, WSMsgType

from kiwoom.config.http import WEBSOCKET_HEARTBEAT, State
from kiwoom.http.utils import cancel


class Socket:
    REAL = "wss://api.kiwoom.com:10000"
    MOCK = "wss://mockapi.kiwoom.com:10000"  # KRX Only
    ENDPOINT = "/api/dostk/websocket"

    def __init__(self, url: str, queue: asyncio.Queue):
        """
        Initialize Socket class.

        Args:
            url (str): url of Kiwoom websocket server
            queue (asyncio.Queue): queue to put received data
        """
        self.url = url
        self._queue = queue
        self._session: ClientSession | None = None
        self._websocket: ClientWebSocketResponse | None = None

        self._state = State.CLOSED
        self._state_lock = asyncio.Lock()
        self._queue_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._stop_event.set()

    async def connect(self, session: ClientSession, token: str):
        """
        Connect to Kiwoom websocket server.

        Args:
            session (ClientSession): aiohttp ClientSession from API.connect()
            token (str): token for authentication
        """

        # print("Trying to connect websocket...")
        async with self._state_lock:
            if self._state in (State.CONNECTED, State.CONNECTING):
                return

            self._state = State.CONNECTING
            try:
                # Close existing websocket & task
                self._stop_event.set()
                if self._websocket and not self._websocket.closed:
                    await self._websocket.close()
                await cancel(self._queue_task)
                self._queue_task = None

                self._session = session
                self._websocket = await session.ws_connect(
                    self.url, autoping=True, heartbeat=WEBSOCKET_HEARTBEAT
                )

                self._stop_event.clear()
                self._queue_task = asyncio.create_task(self.run(), name="enqueue")
                await self.send({"trnm": "LOGIN", "token": token})
                self._state = State.CONNECTED

            except Exception as err:
                print(f"Websocket failed to connect to {self.url}: {err}")
                self._state = State.CLOSED

    async def close(self):
        """
        Close the websocket and the task.
        """
        async with self._state_lock:
            self._stop_event.set()
            if self._queue_task:
                self._queue_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._queue_task

            if self._websocket and not self._websocket.closed:
                with contextlib.suppress(Exception):
                    await self._websocket.close()

            self._session = None
            self._websocket = None
            self._queue_task = None

    async def send(self, msg: str | dict) -> None:
        """
        Send data to Kiwoom websocket server.

        Args:
            msg (str | dict): msg should be in json format
        """
        if isinstance(msg, dict):
            # msg = json.dumps(msg)  # slow
            msg = orjson.dumps(msg).decode("utf-8")
        await self._websocket.send_str(msg)

    async def recv(self) -> str:
        """
        Receive data from Kiwoom websocket server and return data.
        If message type is not str, close the websocket and raise RuntimeError.

        Raises:
            RuntimeError: Websocket Connection Error

        Returns:
            str: received json formatted data from websocket
        """
        try:
            return await self._websocket.receive_str()
        except WSMessageTypeError as err:
            msg = await self._websocket.receive()
            if msg.type == WSMsgType.BINARY:
                msg.data = msg.data.decode("utf-8")
            await self.close()
            raise RuntimeError(f"Websocket received other type than str: {msg}") from err

    async def run(self):
        """
        Receive data from websocket and put data to the queue.
        If WEBSOCKET_QUEUE_MAX_SIZE is set and queue gets full,
        then backpressure will be applied to the websocket.
        Run this task in background with asyncio.create_task().
        """
        assert self._websocket is not None
        try:
            while not self._stop_event.is_set():
                await self._queue.put(await self.recv())

        except Exception as e:
            print(f"Failed to receive message: {e}")
            await self.close()
