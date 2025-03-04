from datetime import datetime
from pathlib import Path

import pytest
import requests

from logbook.models.log_entry import FunctionType
from vereinsflieger.models import Flight, Person
from vereinsflieger.vereinsflieger_api import VereinsfliegerApiSession


def test_raise_for_status_raw(requests_mock):
    requests_mock.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", status_code=403)

    with pytest.raises(requests.exceptions.HTTPError):
        VereinsfliegerApiSession("app_key", "username", "password").sign_in()


def test_raise_for_status_auth(requests_mock):
    requests_mock.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", status_code=404)

    vs = VereinsfliegerApiSession("app_key", "username", "password")
    vs._access_token = "foo"

    with pytest.raises(requests.exceptions.HTTPError):
        vs.get_flight(123)


def test_sign_in(requests_mock):
    requests_mock.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", text='{"accesstoken": "foo"}')
    requests_mock.post("https://www.vereinsflieger.de/interface/rest/auth/signin")

    vs = VereinsfliegerApiSession("app_key", "username", "password")
    vs.sign_in()

    assert vs._access_token == "foo"
    assert requests_mock.call_count == 2


def test_sign_out(requests_mock):
    requests_mock.delete("https://www.vereinsflieger.de/interface/rest/auth/signout/foo")
    vs = VereinsfliegerApiSession("app_key", "username", "password")
    vs._access_token = "foo"
    vs.sign_out()


def test_context_manager(requests_mock):
    requests_mock.post("https://www.vereinsflieger.de/interface/rest/auth/accesstoken", text='{"accesstoken": "foo"}')
    requests_mock.post("https://www.vereinsflieger.de/interface/rest/auth/signin")
    requests_mock.delete("https://www.vereinsflieger.de/interface/rest/auth/signout/foo")

    with VereinsfliegerApiSession("app_key", "username", "password") as vs:
        assert isinstance(vs, VereinsfliegerApiSession)
        assert vs._access_token == "foo"

    assert requests_mock.call_count == 3


def test_get_flight_no_auth(requests_mock):
    requests_mock.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", text="{}")

    with pytest.raises(ValueError, match="not signed in"):
        VereinsfliegerApiSession("app_key", "username", "password").get_flight(123)


MOCK_PILOT = Person(first_name="Peter", last_name="Pilot")
MOCK_INSTRUCTOR = Person(first_name="Ian", last_name="Instructor")


@pytest.mark.parametrize(
    ("flight_type", "fixture_name", "function_type", "pilot", "copilot"),
    [
        ("PIC", "vf_12256298_pic.json", FunctionType.PIC, MOCK_PILOT, None),
        ("Solo", "vf_12240603_solo.json", FunctionType.PIC, MOCK_PILOT, MOCK_INSTRUCTOR),
        ("Dual", "vf_12154186_dual.json", FunctionType.DUAL, MOCK_INSTRUCTOR, MOCK_PILOT),
    ],
)
def test_get_flight_success(
    requests_mock,
    flight_type: str,
    fixture_name: str,
    function_type: FunctionType,
    pilot: Person,
    copilot: Person | None,
):
    vs = VereinsfliegerApiSession("app_key", "username", "password")
    vs._access_token = "foo"

    mock_data = (Path(__file__).parent / Path(f"fixtures/{fixture_name}")).read_text()
    requests_mock.get("https://www.vereinsflieger.de/interface/rest/flight/get/123", text=mock_data)

    assert vs.get_flight(123) == Flight(
        registration="D-EABC",
        from_aerodrome="EDKA",
        to_aerodrome="EDLN",
        departure_time=datetime.fromisoformat("2023-09-01T10:22:00Z"),
        arrival_time=datetime.fromisoformat("2023-09-01T11:07:00Z"),
        landings=5,
        pilot=pilot,
        copilot=copilot,
        function=function_type,
        remarks=f"Example {flight_type} flight",
    )
