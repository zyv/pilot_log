from datetime import datetime
from pathlib import Path
from unittest import TestCase

import requests
import requests_mock

from logbook.models.log_entry import FunctionType
from vereinsflieger.models import Flight, Person
from vereinsflieger.vereinsflieger_api import VereinsfliegerApiSession


@requests_mock.Mocker()
class VereinsfliegerApiTest(TestCase):
    def test_raise_for_status_raw(self, m):
        m.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", status_code=403)
        with self.assertRaises(requests.exceptions.HTTPError):
            VereinsfliegerApiSession("app_key", "username", "password").sign_in()

    def test_raise_for_status_auth(self, m):
        m.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", status_code=404)
        with self.assertRaises(requests.exceptions.HTTPError):
            vs = VereinsfliegerApiSession("app_key", "username", "password")
            vs._access_token = "foo"
            vs.get_flight(123)

    def test_sign_in(self, m):
        m.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", text='{"accesstoken": "foo"}')
        m.post("https://www.vereinsflieger.de/interface/rest/auth/signin")

        vs = VereinsfliegerApiSession("app_key", "username", "password")
        vs.sign_in()

        self.assertEqual("foo", vs._access_token)
        self.assertEqual(2, m.call_count)

    def test_sign_out(self, m):
        m.delete("https://www.vereinsflieger.de/interface/rest/auth/signout/foo")
        vs = VereinsfliegerApiSession("app_key", "username", "password")
        vs._access_token = "foo"
        vs.sign_out()

    def test_context_manager(self, m):
        m.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", text='{"accesstoken": "foo"}')
        m.post("https://www.vereinsflieger.de/interface/rest/auth/signin")
        m.delete("https://www.vereinsflieger.de/interface/rest/auth/signout/foo")
        with VereinsfliegerApiSession("app_key", "username", "password") as vs:
            self.assertIsInstance(vs, VereinsfliegerApiSession)
            self.assertEqual("foo", vs._access_token)
        self.assertEqual(3, m.call_count)

    def test_get_flight_no_auth(self, m):
        m.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", text="{}")
        with self.assertRaises(ValueError):
            VereinsfliegerApiSession("app_key", "username", "password").get_flight(123)

    def test_get_flight_success(self, m):
        vs = VereinsfliegerApiSession("app_key", "username", "password")
        vs._access_token = "foo"

        mock_pilot = Person(first_name="Peter", last_name="Pilot")
        mock_instructor = Person(first_name="Ian", last_name="Instructor")

        for test_name, mock_file, function_type, pilot, copilot in (
            ("PIC", "vf_12256298_pic.json", FunctionType.PIC, mock_pilot, None),
            ("Solo", "vf_12240603_solo.json", FunctionType.PIC, mock_pilot, mock_instructor),
            ("Dual", "vf_12154186_dual.json", FunctionType.DUAL, mock_instructor, mock_pilot),
        ):
            with self.subTest(test_name):
                mock_data = (Path(__file__).parent / Path(f"fixtures/{mock_file}")).read_text()
                m.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", text=mock_data)

                flight_data = vs.get_flight(123)

                self.assertEqual(
                    Flight(
                        registration="D-EABC",
                        from_aerodrome="EDKA",
                        to_aerodrome="EDLN",
                        departure_time=datetime.fromisoformat("2023-09-01T10:22:00Z"),
                        arrival_time=datetime.fromisoformat("2023-09-01T11:07:00Z"),
                        landings=5,
                        pilot=pilot,
                        copilot=copilot,
                        function=function_type,
                        remarks=f"Example {test_name} flight",
                    ),
                    flight_data,
                )
