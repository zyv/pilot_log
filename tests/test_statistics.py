from datetime import UTC, datetime, timedelta

from django.test import TestCase

from logbook.models.aerodrome import Aerodrome
from logbook.models.aircraft import Aircraft, AircraftType
from logbook.models.log_entry import LogEntry
from logbook.models.pilot import Pilot
from logbook.statistics.currency import CurrencyStatus, get_rolling_currency


class TestRollingCurrency(TestCase):
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
        currency = get_rolling_currency(LogEntry.objects.all(), 5)

        self.assertEqual(timedelta(days=0), currency.expires_in)
        self.assertEqual(datetime.now(tz=UTC).date(), currency.expires_on)
        self.assertEqual(CurrencyStatus.NOT_CURRENT, currency.status)
        self.assertEqual(5, currency.landings_to_renew)

    def test_current(self):
        number_of_entries = 30

        for i in range(number_of_entries):
            LogEntry.objects.create(
                aircraft=self.aircraft,
                from_aerodrome=self.airport,
                to_aerodrome=self.airport,
                departure_time=datetime.now(tz=UTC) - timedelta(days=110 - i),
                arrival_time=datetime.now(tz=UTC) - timedelta(days=110 - i) + timedelta(seconds=1),
                landings=1,
                pilot=self.pilot,
            )

        with self.subTest("linear progression"):
            currency = get_rolling_currency(LogEntry.objects.all(), 5)

            self.assertAlmostEqual(
                timedelta(days=5).total_seconds() / 60,
                currency.expires_in.total_seconds() / 60,
                places=1,
            )

            self.assertEqual((datetime.now(tz=UTC) + timedelta(days=5 - 1)).date(), currency.expires_on)
            self.assertEqual(CurrencyStatus.EXPIRING, currency.status)
            self.assertEqual(1, currency.landings_to_renew)

        with self.subTest("first current and expired on same day"):
            first_current_entry = LogEntry.objects.get(pk=number_of_entries)
            first_current_entry.pk = None
            first_current_entry.landings = 7
            first_current_entry.departure_time -= timedelta(hours=1)
            first_current_entry.arrival_time -= timedelta(hours=1)
            first_current_entry.save()

            currency = get_rolling_currency(LogEntry.objects.all(), 5)

            self.assertAlmostEqual(
                timedelta(days=8, hours=23).total_seconds() / 60,
                currency.expires_in.total_seconds() / 60,
                places=1,
            )

            self.assertEqual((datetime.now(tz=UTC) + timedelta(days=8)).date(), currency.expires_on)
            self.assertEqual(CurrencyStatus.EXPIRING, currency.status)
            self.assertEqual(5, currency.landings_to_renew)

    def test_lowest_currency_status(self):
        self.assertEqual(CurrencyStatus.CURRENT, min(CurrencyStatus.CURRENT, CurrencyStatus.CURRENT))
        self.assertEqual(CurrencyStatus.EXPIRING, min(CurrencyStatus.CURRENT, CurrencyStatus.EXPIRING))
        self.assertEqual(CurrencyStatus.NOT_CURRENT, min(CurrencyStatus.EXPIRING, CurrencyStatus.NOT_CURRENT))
