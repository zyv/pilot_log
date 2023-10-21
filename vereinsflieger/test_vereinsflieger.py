from unittest import TestCase

import requests_mock

from vereinsflieger.vereinsflieger import VereinsfliegerSession


class VereinsfliegerTest(TestCase):
    @requests_mock.Mocker()
    def test_sign_in(self, m):
        m.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", text='{"accesstoken": "foo"}')
        m.post("https://www.vereinsflieger.de/interface/rest/auth/signin")

        vs = VereinsfliegerSession("app_key", "username", "password")
        vs.sign_in()

        self.assertEqual(vs._access_token, "foo")

    @requests_mock.Mocker()
    def test_sign_out(self, m):
        m.delete("https://www.vereinsflieger.de/interface/rest/auth/signout/foo")
        vs = VereinsfliegerSession("app_key", "username", "password")
        vs._access_token = "foo"
        vs.sign_out()

    @requests_mock.Mocker()
    def test_context_manager(self, m):
        m.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", text='{"accesstoken": "foo"}')
        m.post("https://www.vereinsflieger.de/interface/rest/auth/signin")
        m.delete("https://www.vereinsflieger.de/interface/rest/auth/signout/foo")
        with VereinsfliegerSession("app_key", "username", "password") as _:
            pass

    @requests_mock.Mocker()
    def test_get_flight_no_token(self, m):
        m.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", text="{}")
        with self.assertRaises(ValueError):
            VereinsfliegerSession("app_key", "username", "password").get_flight(123)

    @requests_mock.Mocker()
    def test_get_flight(self, m):
        m.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", text="{}")
        vs = VereinsfliegerSession("app_key", "username", "password")
        vs._access_token = "foo"
        vs.get_flight(123)
