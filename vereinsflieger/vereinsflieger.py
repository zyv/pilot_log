import hashlib
from functools import wraps

import requests


class VereinsfliegerSession:
    BASE_URL = "https://www.vereinsflieger.de/interface/rest"

    def __init__(self, app_key: str, username: str, password: str):
        self.app_key = app_key
        self.username = username
        self.password = password

        self._access_token = None
        self.raw_session = requests.Session()

        def authenticated_request(request_function):
            @wraps(request_function)
            def wrapper(*args, **kwargs):
                if self._access_token is None:
                    raise ValueError("not signed in")
                kwargs["data"] = kwargs.get("data", {}) | {"accesstoken": self._access_token}
                return request_function(*args, **kwargs)

            return wrapper

        self.session = requests.Session()
        self.session.request = authenticated_request(self.session.request)

    def __enter__(self):
        self.sign_in()
        return self

    def __exit__(self, type, value, traceback):
        self.sign_out()

    def sign_in(self):
        if self.username is None or self.password is None:
            raise ValueError("username or password not set")

        response = self.raw_session.post(f"{self.BASE_URL}/auth/accesstoken")
        response.raise_for_status()

        self._access_token = response.json()["accesstoken"]
        password_hash = hashlib.md5(self.password.encode("iso-8859-1")).hexdigest()

        response = self.session.post(
            f"{self.BASE_URL}/auth/signin",
            data={
                "username": self.username,
                "password": password_hash,
                "cid": 0,
                "appkey": self.app_key,
                "auth_secret": "",
            },
        )
        response.raise_for_status()

    def sign_out(self):
        response = self.session.delete(f"{self.BASE_URL}/auth/signout/{self._access_token}")
        response.raise_for_status()

    def get_flight(self, fid: int):
        response = self.session.get(f"{self.BASE_URL}/flight/get/{fid}")
        response.raise_for_status()

        return response.json()
