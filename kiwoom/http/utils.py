import json

from requests.models import Response
from requests.exceptions import HTTPError


@staticmethod
def dumps(api, endpoint: str, api_id, headers: dict, data: dict, res: Response) -> str:
    # Request
    headers = json.dumps(
        headers if headers else api.headers(api_id),
        indent=4,
        ensure_ascii=False
    )
    req = '\n== Request ==\n'
    req += f'URL : {api.host + endpoint}\n'
    req += f'Headers : {headers}\n'
    req += f'Data : {json.dumps(data, indent=4, ensure_ascii=False)}\n'

    # Response
    headers = json.dumps(
        {key: res.headers.get(key) for key in ['next-key', 'cont-yn', 'api-id']},
        indent=4,
        ensure_ascii=False
    )
    resp = '== Response ==\n'
    resp += f'Code : {res.status_code}\n'
    resp += f'Headers : {headers}\n'
    resp += f'Response : {json.dumps(res.json(), indent=4, ensure_ascii=False)}\n'
    return req + resp


@staticmethod
def debugger(fn):
    async def wrapper(api, endpoint, api_id, headers, data):
        res = await fn(api, endpoint, api_id, headers, data)
        if getattr(api, "debugging"):
            print(dumps(api, endpoint, api_id, headers, data, res))
        
        try:
            res.raise_for_status()
        except HTTPError as err:
            # Always debug when error occurs
            if not getattr(api, "debugging"):
                print(dumps(api, endpoint, api_id, headers, data, res))
            raise err
        return res
    return wrapper
