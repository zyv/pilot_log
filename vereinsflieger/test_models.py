from datetime import datetime

from .models import Flight, Person


def test_parse_pilot():
    assert Flight.parse_pilot("van Pilot, Peter") == Person(first_name="Peter", last_name="van Pilot")


def test_parse_location():
    assert Flight.parse_location("Köln Bonn EDDK") == "EDDK"


def test_parse_datetime():
    assert Flight.parse_datetime("2021-01-01", "12:00") == datetime.fromisoformat("2021-01-01T12:00+00:00")
