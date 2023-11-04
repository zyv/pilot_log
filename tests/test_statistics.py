from datetime import UTC, datetime, timedelta

from django.test import TestCase

from logbook.models import Aerodrome, Aircraft, AircraftType, LogEntry, Pilot
from logbook.statistics.currency import CurrencyStatus, get_ninety_days_currency


class TestNinetyDaysCurrency(TestCase):
    def setUp(self):
        self.aircraft = Aircraft.objects.create(
            type=AircraftType.SEP,
            maker="Test",
            model="Test",
            icao_designator="TEST",
            registration="TEST",
        )
        self.pilot = Pilot.objects.create(
            first_name="Test",
            last_name="Test",
        )
        self.airport = Aerodrome.objects.create(
            name="Test",
            city="Test",
            country="DE",
            icao_code="TEST",
            latitude=0,
            longitude=0,
            elevation=0,
            priority=0,
        )

    def test_not_current(self):
        currency = get_ninety_days_currency(LogEntry.objects.all(), 5)

        self.assertEqual(timedelta(days=0), currency.expires_in)
        self.assertEqual(datetime.now(tz=UTC).date(), currency.expires_on)
        self.assertEqual(CurrencyStatus.NOT_CURRENT, currency.status)
        self.assertEqual(5, currency.landings_to_renew)

    def test_current(self):
        for i in range(30):
            LogEntry.objects.create(
                aircraft=self.aircraft,
                from_aerodrome=self.airport,
                to_aerodrome=self.airport,
                departure_time=datetime.now(tz=UTC) - timedelta(days=110 - i),
                arrival_time=datetime.now(tz=UTC) - timedelta(days=110 - i),
                landings=1,
                pilot=self.pilot,
            )

        currency = get_ninety_days_currency(LogEntry.objects.all(), 5)

        self.assertAlmostEquals(
            timedelta(days=5).total_seconds() / 60,
            currency.expires_in.total_seconds() / 60,
            places=1,
        )
        self.assertEqual(datetime.now(tz=UTC).date() + timedelta(days=4), currency.expires_on)
        self.assertEqual(CurrencyStatus.EXPIRING, currency.status)
        self.assertEqual(1, currency.landings_to_renew)
