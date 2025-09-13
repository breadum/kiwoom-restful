import functools
import json
from typing import Callable

from aiohttp import ClientResponse
from aiohttp.web import HTTPException

from kiwoom.http.response import Response

__all__ = ["dumps", "debugger"]


def dumps(api, endpoint: str, api_id, headers: dict, data: dict, res: Response) -> str:
    """
    Dump request and response to string for debugging.

    Args:
        api (Client): Client instance
        endpoint (str): endpoint
        api_id (str): api id
        headers (dict): headers
        data (dict): data
        res (Response): wrapped response

    Returns:
        str: _description_
    """
    # Request
    headers = json.dumps(
        headers if headers is not None else api.headers(api_id), indent=4, ensure_ascii=False
    )
    req = "\n== Request ==\n"
    req += f"URL : {api.host + endpoint}\n"
    req += f"Headers : {headers}\n"
    req += f"Data : {json.dumps(data, indent=4, ensure_ascii=False)}\n"

    # Response
    headers = json.dumps(
        {key: res.headers.get(key) for key in ["next-key", "cont-yn", "api-id"]},
        indent=4,
        ensure_ascii=False,
    )
    resp = "== Response ==\n"
    resp += f"Code : {res.status}\n"
    resp += f"Headers : {headers}\n"
    resp += f"Response : {json.dumps(res.json(), indent=4, ensure_ascii=False)}\n"
    return req + resp


def debugger(fn) -> Callable:
    """
    Debugger decorator for Client.post method.
    Even though debugging is disabled, it will print if error occurs.

    Args:
        fn (function): function to be decorated

    Raises:
        err: propagate HTTPException from original function

    Returns:
        Response: wrapped response
    """

    @functools.wraps(fn)
    async def wrapper(api, endpoint: str, api_id: str, headers: dict, data: dict) -> Response:
        res: ClientResponse = await fn(api, endpoint, api_id, headers, data)
        async with res:
            # Async to sync Response
            resp = Response(
                url=res.url, status=res.status, headers=res.headers, body=await res.json()
            )

            # Debugging
            if api.debugging:
                print(dumps(api, endpoint, api_id, headers, data, resp))

            try:
                res.raise_for_status()
            except HTTPException as err:
                # Always debug when error occurs
                if not api.debugging:
                    print(dumps(api, endpoint, api_id, headers, data, resp))
                raise err
        return resp

    return wrapper
