import hashlib
import logging
from functools import partial

import httpx

from .models import Flight

logger = logging.getLogger(__name__)


class VereinsfliegerError(Exception):
    pass


class HttpClient(httpx.Client):
    BASE_URL_VEREINSFLIEGER = "https://www.vereinsflieger.de/interface/rest"
    BASE_URL_FLIGHTCENTER = "https://www.flightcenterplus.de/interface/rest"

    @staticmethod
    def log_vereinsflieger_request(request: httpx.Request):
        logger.debug(f"VF API Request: {request.method} {request.url} {request.content.decode()}")

    @staticmethod
    def log_vereinsflieger_response(response: httpx.Response):
        request = response.request
        response.read()
        logger.debug(f"VF API Response: {request.method} {request.url} {response.status_code} {response.text}")

    @staticmethod
    def inject_access_token(access_token: str, request: httpx.Request):
        request.url = request.url.copy_set_param("accesstoken", access_token)

    @staticmethod
    def raise_if_not_signed_in(request: httpx.Request):
        raise VereinsfliegerError("not signed in")

    def __init__(self, **kwargs):
        super().__init__(
            event_hooks={
                "request": [HttpClient.log_vereinsflieger_request],
                "response": [HttpClient.log_vereinsflieger_response, httpx.Response.raise_for_status],
            },
            **kwargs,
        )


class VereinsfliegerApiSession:
    def __init__(
        self,
        app_key: str,
        username: str,
        password: str,
        cid: int = 0,
        http_client: type[httpx.Client] | None = None,
    ):
        self._app_key = app_key
        self._username = username
        self._password = password
        self._cid = cid

        self._http_client = (
            http_client if http_client is not None else HttpClient(base_url=HttpClient.BASE_URL_VEREINSFLIEGER)
        )

        self._access_token_hook = None
        self._add_sign_in_guard_hook()

    def __enter__(self) -> "VereinsfliegerApiSession":
        self.sign_in()
        return self

    def __exit__(self, type, value, traceback):
        self.sign_out()

    def _add_sign_in_guard_hook(self):
        if HttpClient.raise_if_not_signed_in not in self._http_client.event_hooks["request"]:
            self._http_client.event_hooks["request"].append(HttpClient.raise_if_not_signed_in)
        else:
            raise VereinsfliegerError("sign in guard already set")

    def _remove_sign_in_guard_hook(self):
        self._http_client.event_hooks["request"].remove(HttpClient.raise_if_not_signed_in)

    def _remove_access_token_hook(self):
        self._http_client.event_hooks["request"].remove(self._access_token_hook)
        self._access_token_hook = None

    def _add_access_token_hook(self, access_token: str):
        self._access_token_hook = partial(HttpClient.inject_access_token, access_token)
        self._http_client.event_hooks["request"].append(self._access_token_hook)

    def sign_in(self):
        def authenticate():
            response = self._http_client.post("/auth/accesstoken")

            self._add_access_token_hook(response.json()["accesstoken"])
            try:
                self._http_client.post(
                    "/auth/signin",
                    params={
                        "username": self._username,
                        "password": hashlib.md5(self._password.encode("iso-8859-1")).hexdigest(),
                        "cid": self._cid,
                        "appkey": self._app_key,
                        "auth_secret": "",
                    },
                )
            except:
                self._remove_access_token_hook()
                raise

        self._remove_sign_in_guard_hook()
        try:
            authenticate()
        except:
            self._add_sign_in_guard_hook()
            raise

    def sign_out(self):
        (access_token,) = self._access_token_hook.args if self._access_token_hook is not None else (None,)
        self._http_client.delete(f"/auth/signout/{access_token}")
        self._add_sign_in_guard_hook()
        self._remove_access_token_hook()

    def get_flight(self, fid: int) -> Flight:
        response = self._http_client.get(f"/flight/get/{fid}")
        return Flight.from_vereinsflieger_api(response.json())
