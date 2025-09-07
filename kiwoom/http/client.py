import asyncio

from typing import Callable
from os.path import isfile
from itertools import chain

from requests import Session
from requests.models import Response

from kiwoom.config import REQ_LIMIT_TIME
from kiwoom.http import utils as Http


class Client:
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
        res = self._session.post(
            self.host + endpoint,
            headers=headers,
            json=data
        )
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
    
    @Http.debugger
    async def post(
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
    
    async def request(
        self, 
        endpoint: str, 
        api_id: str, 
        headers: dict = {}, 
        data: dict = {}
    ) -> Response:
        
        res = await self.post(endpoint, api_id, headers=headers, data=data)
        body = res.json()
        if 'return_code' in body:
            match body['return_code']:
                case 0 | 20:
                    # 0: Success
                    # 20 : No Data
                    return res
                case 3:
                    # 3 : Token Expired
                    await self.init(self._appkey, self._secretkey)
                    return await self.request(
                        endpoint, 
                        api_id, 
                        headers=headers, 
                        data=data
                    )
        
        # Request Failure
        msg = Http.dumps(self, endpoint, api_id, headers, data, res)
        raise RuntimeError(msg)
    
    async def request_until(
        self, 
        should_continue: Callable,
        endpoint: str, 
        api_id: str, 
        headers: dict = {}, 
        data: dict = {},
    ) -> dict:
        """
        Request until 'cont-yn' in response header is 'Y',
        and should_continue(body) evaluates to True.

        * should_continue : callable that takes body(dict) and \
                            returns boolean value to request again or not
        """
        await asyncio.sleep(REQ_LIMIT_TIME)
        res = await self.request(endpoint, api_id, headers=headers, data=data)
        body = res.json()
        
        # Condition to chain is not met
        if callable(should_continue) and not should_continue(body):
            return body
        
        bodies = dict()
        for key in body.keys():
            if isinstance(body[key], list):
                bodies[key] = [body[key]]
                continue
            bodies[key] = body[key]
        
        while res.headers.get('cont-yn') == 'Y' and should_continue(body):
            next_key = res.headers.get('next-key')
            headers = self.headers(
                api_id, 
                cont_yn='Y', 
                next_key=next_key, 
                headers=headers
            )
            
            # Rercursive call
            await asyncio.sleep(REQ_LIMIT_TIME)
            res = await self.request(endpoint, api_id, headers=headers, data=data)
            body = res.json()
            
            for key in body.keys():
                if isinstance(body[key], list):
                    bodies[key].append(body[key])
        
        for key in bodies:
            if isinstance(bodies[key], list):
                bodies[key] = list(chain.from_iterable(bodies[key]))
        return bodies
    