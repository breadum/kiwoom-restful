import json
import requests
import asyncio

from typing import Callable
from os.path import isfile
from requests import Session
from requests.models import Response

from kiwoom.config import REQ_LIMIT_TIME


class API:
    def __init__(self, host: str, appkey: str, secretkey: str):
        self.debugging: bool = False
        self.host: str = host
        self._auth: str = ''
        self._appkey: str = appkey
        self._secretkey: str = secretkey
        self._session: Session = None
        self.init(appkey, secretkey)

    def init(self, appkey: str, secretkey: str):
        """
        appkey, scretkey : string | file path
        """
        if isfile(appkey):
            with open(appkey, 'r') as f:
                self._appkey = f.read().strip()
        if isfile(secretkey):
            with open(secretkey, 'r') as f:
                self._secretkey = f.read().strip()
        if self._session:
            try:
                self._session.close()
            except:
                pass
        
        self._session = Session()
        endpoint = '/oauth2/token'
        headers = self.headers(api_id='')
        data = {
            'grant_type': 'client_credentials',
            'appkey': self._appkey,
            'secretkey': self._secretkey
        }
        res = self.post(endpoint, api_id='', headers=headers, data=data)
        res.raise_for_status()
        data = res.json()
        token = data['token']
        self._auth = f'Bearer {token}'

    def headers(
        self, 
        api_id: str, 
        cont_yn: str = 'N', 
        next_key: str = '',
        headers: dict = {}
    ) -> dict[str, str]:
        
        base = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': self._auth,
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': api_id
        }
        if headers:
            headers.update(base)
            return headers
        return base 
    
    def post(
        self, 
        endpoint: str, 
        api_id: str, 
        headers: dict = {}, 
        data: dict = {}
    ) -> Response:

        if not headers:
            headers = self.headers(api_id)
        return self._session.post(
            self.host + endpoint,
            headers=headers,
            json=data
        )
    
    def request(
        self, 
        endpoint: str, 
        api_id: str, 
        headers: dict = {}, 
        data: dict = {}
    ) -> Response:
        
        res = self.post(endpoint, api_id, headers=headers, data=data)
        if self.debugging:
            print(self.debug(endpoint, api_id, headers, data, res))
        res.raise_for_status()
        body = res.json()
        if 'return_code' in body:
            match body['return_code']:
                case 0 | 20:
                    # 0: Success
                    # 20 : No Data
                    return res
                case 3:
                    # 3 : Token Expired
                    self.init(self._appkey, self._secretkey)
                    return self.request(endpoint, api_id, headers=headers, data=data)
        
        # Request Failure
        msg = self.debug(endpoint, api_id, headers, data, res)
        raise RuntimeError(msg)
    
    async def chain_request(
        self, 
        cond: Callable,
        endpoint: str, 
        api_id: str, 
        headers: dict = {}, 
        data: dict = {},
    ) -> dict:
        """
        Note that cond argument is used in decorator.
        cond : any callable that takes body(dict) and returns request again or not
        """
        await asyncio.sleep(REQ_LIMIT_TIME)
        res = self.request(endpoint, api_id, headers=headers, data=data)
        body = res.json()
        
        # Condition to chain is not met
        if callable(cond) and not cond(body):
            return body
        
        if res.headers.get('cont-yn') == 'Y':
            next_key = res.headers.get('next-key')
            headers = self.headers(
                api_id, 
                cont_yn='Y', 
                next_key=next_key, 
                headers=headers
            )
            
            # Rercursive call
            await asyncio.sleep(REQ_LIMIT_TIME)
            rbody = await self.chain_request(
                cond, 
                endpoint, 
                api_id, 
                headers=headers, 
                data=data
            )
            for key in rbody.keys():
                if isinstance(rbody[key], list):
                    body[key].extend(rbody[key])
        return body
    
    def debug(self, endpoint: str, api_id, headers: dict, data: dict, res: Response) -> str:
        # Request
        headers = json.dumps(
            headers if headers else self.headers(api_id),
            indent=4,
            ensure_ascii=False
        )
        req = '\n== Request ==\n'
        req += f'URL : {self.host + endpoint}\n'
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
