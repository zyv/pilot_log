from datetime import datetime
from pathlib import Path

import httpx
import pytest
import respx

from logbook.models.log_entry import FunctionType
from vereinsflieger.models import Flight, Person
from vereinsflieger.vereinsflieger_api import HttpClient, VereinsfliegerApiSession, VereinsfliegerError

pytestmark = pytest.mark.respx(base_url="https://www.vereinsflieger.de")


@pytest.fixture
def vf_session() -> VereinsfliegerApiSession:
    return VereinsfliegerApiSession("app_key", "username", "password")


@pytest.fixture
def respx_mock_sign_in(respx_mock: respx.mock) -> respx.mock:
    respx_mock.post(url="/interface/rest/auth/accesstoken", params="").respond(json={"accesstoken": "foo"})
    respx_mock.post(
        url="/interface/rest/auth/signin",
        params={
            "accesstoken": "foo",
            "username": "username",
            "password": "5f4dcc3b5aa765d61d8327deb882cf99",
            "cid": 0,
            "appkey": "app_key",
            "auth_secret": "",
        },
    ) % httpx.codes.OK

    return respx_mock


def test_sign_in_raise_for_status_access_token(respx_mock: respx.mock, vf_session: VereinsfliegerApiSession):
    respx_mock.post(url="/interface/rest/auth/accesstoken") % httpx.codes.FORBIDDEN

    with pytest.raises(httpx.HTTPError):
        vf_session.sign_in()

    assert vf_session._access_token_hook is None
    with pytest.raises(VereinsfliegerError, match="not signed in"):
        vf_session.get_flight(123)

    with pytest.raises(httpx.HTTPError):
        vf_session.sign_in()

    assert vf_session._access_token_hook is None
    assert respx_mock.calls.call_count == 2


def test_sign_in_raise_for_status_sign_in(respx_mock: respx.mock, vf_session: VereinsfliegerApiSession):
    respx_mock.post(url="/interface/rest/auth/accesstoken").respond(json={"accesstoken": "foo"})
    respx_mock.post(url="/interface/rest/auth/signin") % httpx.codes.FORBIDDEN

    with pytest.raises(httpx.HTTPStatusError):
        vf_session.sign_in()

    assert vf_session._access_token_hook is None
    with pytest.raises(VereinsfliegerError, match="not signed in"):
        vf_session.get_flight(123)

    assert respx_mock.calls.call_count == 2


def test_raise_if_not_signed_in(vf_session: VereinsfliegerApiSession):
    with pytest.raises(VereinsfliegerError, match="not signed in"):
        vf_session.sign_out()

    with pytest.raises(VereinsfliegerError, match="not signed in"):
        vf_session.get_flight(123)


def test_sign_out(respx_mock_sign_in: respx.mock, vf_session: VereinsfliegerApiSession):
    respx_mock_sign_in.delete(url="/interface/rest/auth/signout/foo", params={"accesstoken": "foo"}) % httpx.codes.OK
    vf_session.sign_in()
    vf_session.sign_out()


def test_session_context_manager(respx_mock_sign_in: respx.mock):
    respx_mock_sign_in.delete(url="/interface/rest/auth/signout/foo", params={"accesstoken": "foo"}) % httpx.codes.OK

    with VereinsfliegerApiSession("app_key", "username", "password") as vs:
        assert isinstance(vs, VereinsfliegerApiSession)
        assert vs._access_token_hook.args == ("foo",)

    assert vs._access_token_hook is None
    assert HttpClient.raise_if_not_signed_in in vs._http_client.event_hooks["request"]
    assert respx_mock_sign_in.calls.call_count == 3


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
    respx_mock_sign_in: respx.mock,
    flight_type: str,
    fixture_name: str,
    function_type: FunctionType,
    pilot: Person,
    copilot: Person | None,
):
    respx_mock_sign_in.get(url="/interface/rest/flight/get/123").respond(
        content=(Path(__file__).parent / Path(f"fixtures/{fixture_name}")).read_bytes()
    )
    respx_mock_sign_in.delete(url="/interface/rest/auth/signout/foo", params={"accesstoken": "foo"}) % httpx.codes.OK

    with VereinsfliegerApiSession("app_key", "username", "password") as vs:
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
