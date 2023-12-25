from datetime import datetime
from unittest import TestCase

from .models import Flight, Person


class ModelsTest(TestCase):
    def test_parse_pilot(self):
        self.assertEqual(Person(first_name="Peter", last_name="van Pilot"), Flight.parse_pilot("van Pilot, Peter"))

    def test_parse_location(self):
        self.assertEqual("EDDK", Flight.parse_location("Köln Bonn EDDK"))

    def test_parse_datetime(self):
        self.assertEqual(
            datetime.fromisoformat("2021-01-01T12:00+00:00"),
            Flight.parse_datetime("2021-01-01", "12:00"),
        )
