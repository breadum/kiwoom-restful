import asyncio
from itertools import chain
from os.path import isfile
from typing import Callable

import aiohttp
from aiohttp import ClientSession

from kiwoom.config.http import (
    HTTP_CONNECT_TIMEOUT,
    HTTP_READ_TIMEOUT,
    HTTP_TCP_CONNECTORS,
    HTTP_TOTAL_TIMEOUT,
)
from kiwoom.http.debug import debugger, dumps
from kiwoom.http.response import Response
from kiwoom.http.utils import RateLimiter

__all__ = ["Client"]


class Client:
    def __init__(self, host: str, appkey: str, secretkey: str):
        """
        Initialize Client instance.

        Args:
            host (str): domain
            appkey (str): file path or raw appkey
            secretkey (str): file path or raw secretkey
        """
        self.host: str = host
        self.debugging: bool = False

        self._auth: str = ""
        self._appkey: str = appkey
        self._secretkey: str = secretkey

        self._ready_event = asyncio.Event()
        self._limiter: RateLimiter = RateLimiter()
        self._session: ClientSession = None

    async def connect(self, appkey: str, secretkey: str) -> None:
        """
        Connect to Kiwoom REST API server and receive token.

        Args:
            appkey (str): file path or raw appkey
            secretkey (str): file path or raw secretkey
        """
        if isfile(appkey):
            with open(appkey, "r") as f:
                self._appkey = f.read().strip()
        if isfile(secretkey):
            with open(secretkey, "r") as f:
                self._secretkey = f.read().strip()

        # Already connected
        if self._session and not self._session.closed:
            return

        # Establish HTTP session
        self._ready_event.clear()
        self._session = ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=HTTP_TOTAL_TIMEOUT,
                sock_connect=HTTP_CONNECT_TIMEOUT,
                sock_read=HTTP_READ_TIMEOUT,
            ),
            connector=aiohttp.TCPConnector(limit=HTTP_TCP_CONNECTORS, enable_cleanup_closed=True),
        )

        # Request token
        endpoint = "/oauth2/token"
        headers = self.headers(api_id="")
        data = {
            "grant_type": "client_credentials",
            "appkey": self._appkey,
            "secretkey": self._secretkey,
        }
        async with self._session.post(self.host + endpoint, headers=headers, json=data) as res:
            res.raise_for_status()
            data = await res.json()

        # Set token
        token = data["token"]
        self._auth = f"Bearer {token}"
        self._session.headers.update(
            {
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": self._auth,
            }
        )
        self._ready_event.set()

    async def close(self) -> None:
        """
        Close HTTP session.
        """
        self._ready_event.clear()
        if self._session:
            await asyncio.shield(self._session.close())

        self._auth = ""
        self._session = None

    def token(self) -> str:
        """
        Returns token if available, otherwise empty string.

        Raises:
            ValueError: Invalid token.

        Returns:
            str: token
        """
        if not self._auth:
            return ""
        if "Bearer " in self._auth:
            return self._auth[len("Bearer ") :]
        raise ValueError(f"Invalid token: {self._auth}")

    def headers(
        self, api_id: str, cont_yn: str = "N", next_key: str = "", headers: dict | None = None
    ) -> dict[str, str]:
        """
        Generate headers for the request.

        Args:
            api_id (str): api_id in Kiwoom API
            cont_yn (str, optional): cont_yn in Kiwoom API
            next_key (str, optional): next_key in Kiwoom API
            headers (dict | None, optional): headers to be updated with

        Returns:
            dict[str, str]: headers
        """
        base = {
            # 'Content-Type': 'application/json;charset=UTF-8',
            # 'authorization': self._auth,
            "cont-yn": cont_yn,
            "next-key": next_key,
            "api-id": api_id,
        }
        if headers is not None:
            headers.update(base)
            return headers
        return base

    async def ready(self):
        """
        Wait until request limit is lifted and connection is established.

        Raises:
            RuntimeError: Connection timeout.
        """
        try:
            await asyncio.wait_for(self._ready_event.wait(), HTTP_TOTAL_TIMEOUT)
        except asyncio.TimeoutError as err:
            msg = f"Connection timeout: waited for {HTTP_TOTAL_TIMEOUT} seconds."
            raise RuntimeError(msg) from err
        await self._limiter.acquire()

    @debugger
    async def post(
        self, endpoint: str, api_id: str, headers: dict | None = None, data: dict | None = None
    ) -> aiohttp.ClientResponse:
        """
        Post request to the server, but using client.request function is recommended.
        Request limit and connection status are checked globally and automatically.

        Args:
            endpoint (str): endpoint to Kiwoom REST API server
            api_id (str): api id
            headers (dict | None, optional): headers of the request.
            data (dict | None, optional): data to be sent in json format

        Returns:
            aiohttp.ClientResponse: async response from the server,
                but this will be converted to kiwoom.http.response.Response by debugger.
        """

        # Check connection and request limits
        await self.ready()

        # Post Request
        if headers is None:
            headers = self.headers(api_id)
        return await self._session.post(self.host + endpoint, headers=headers, json=data)

    async def request(
        self, endpoint: str, api_id: str, headers: dict | None = None, data: dict | None = None
    ) -> Response:
        """
        Requests to the server and returns response with error handling.

        Args:
            endpoint (str): endpoint of the server
            api_id (str): api id
            headers (dict | None, optional): headers of the request. Defaults to None.
            data (dict | None, optional): data of the request. Defaults to None.

        Raises:
            RuntimeError: RuntimeError when return_code is not in [0, 3, 20]

        Returns:
            Response: response wrapped by kiwoom.http.response.Response
        """

        res: Response = await self.post(endpoint, api_id, headers=headers, data=data)
        body = res.json()
        if "return_code" in body:
            match body["return_code"]:
                case 0 | 20:
                    # 0: Success
                    # 20 : No Data
                    return res
                case 3:
                    # 3 : Token Expired
                    print("Token expired, trying to refresh token...")
                    await self.connect(self._appkey, self._secretkey)
                    return await self.request(endpoint, api_id, headers=headers, data=data)

        # Request Failure
        return_code = body["return_code"]
        err = f"\nRequest failed with {return_code=}, not in {{'0', '3', '20'}}."
        if not self.debugging:
            msg = dumps(self, endpoint, api_id, headers, data, res)
            raise RuntimeError(msg + err)
        raise RuntimeError(err)

    async def request_until(
        self,
        should_continue: Callable,
        endpoint: str,
        api_id: str,
        headers: dict | None = None,
        data: dict | None = None,
    ) -> dict:
        """
        Request until 'cont-yn' in response header is 'Y',
        and should_continue(body) evaluates to True.

        Args:
            should_continue (Callable):
                callable that takes body(dict) and
                returns boolean value to request again or not
            endpoint (str):
                endpoint of the server
            api_id (str):
                api id
            headers (dict | None, optional):
                headers of the request. Defaults to None.
            data (dict | None, optional):
                data of the request. Defaults to None.

        Returns:
            dict: response body
        """

        # Initial request
        res = await self.request(endpoint, api_id, headers=headers, data=data)
        body = res.json()

        # If condition to chain is not met
        if callable(should_continue) and not should_continue(body):
            return body

        # Extract list data only
        bodies = dict()
        for key in body.keys():
            if isinstance(body[key], list):
                bodies[key] = [body[key]]
                continue
            bodies[key] = body[key]

        # Rercursive call
        while res.headers.get("cont-yn") == "Y" and should_continue(body):
            next_key = res.headers.get("next-key")
            headers = self.headers(api_id, cont_yn="Y", next_key=next_key, headers=headers)

            # Continue request
            res = await self.request(endpoint, api_id, headers=headers, data=data)
            body = res.json()

            # Append list data
            for key in body.keys():
                if isinstance(body[key], list):
                    bodies[key].append(body[key])

        # Flatten list data as if it was one list
        for key in bodies:
            if isinstance(bodies[key], list):
                bodies[key] = list(chain.from_iterable(bodies[key]))
        return bodies
