from datetime import UTC, datetime, timedelta

import pytest

from logbook.models.aerodrome import Aerodrome
from logbook.models.aircraft import Aircraft, AircraftType
from logbook.models.log_entry import LogEntry
from logbook.models.pilot import Pilot
from logbook.statistics.currency import CurrencyStatus, get_rolling_currency

NUMBER_OF_LOG_ENTRIES = 30


@pytest.fixture
def log_entries():
    aircraft = Aircraft.objects.create(
        type=AircraftType.SEP,
        maker="Test",
        model="Test",
        icao_designator="TEST",
        registration="TEST",
    )
    aerodrome = Aerodrome.objects.create(
        name="Test",
        city="Test",
        country="DE",
        icao_code="TEST",
        latitude=0,
        longitude=0,
        elevation=0,
        priority=0,
    )
    pilot = Pilot.objects.create(first_name="Test", last_name="Test")

    for i in range(NUMBER_OF_LOG_ENTRIES):
        LogEntry.objects.create(
            aircraft=aircraft,
            from_aerodrome=aerodrome,
            to_aerodrome=aerodrome,
            departure_time=datetime.now(tz=UTC) - timedelta(days=110 - i),
            arrival_time=datetime.now(tz=UTC) - timedelta(days=110 - i) + timedelta(seconds=1),
            landings=1,
            pilot=pilot,
        )


@pytest.mark.django_db
def test_not_current():
    currency = get_rolling_currency(LogEntry.objects.all(), 5)

    assert timedelta(days=0) == currency.expires_in
    assert datetime.now(tz=UTC).date() == currency.expires_on
    assert CurrencyStatus.NOT_CURRENT == currency.status
    assert 5 == currency.landings_to_renew


@pytest.mark.django_db
def test_current_linear(log_entries):
    currency = get_rolling_currency(LogEntry.objects.all(), 5)

    assert timedelta(days=5).total_seconds() == pytest.approx(currency.expires_in.total_seconds(), abs=0.1)

    assert (datetime.now(tz=UTC) + timedelta(days=5 - 1)).date() == currency.expires_on
    assert CurrencyStatus.EXPIRING == currency.status
    assert 1 == currency.landings_to_renew


@pytest.mark.django_db
def test_current_first_current_and_expired_on_same_day(log_entries):
    first_current_entry = LogEntry.objects.get(pk=NUMBER_OF_LOG_ENTRIES)
    first_current_entry.pk = None
    first_current_entry.landings = 7
    first_current_entry.departure_time -= timedelta(hours=1)
    first_current_entry.arrival_time -= timedelta(hours=1)
    first_current_entry.save()

    currency = get_rolling_currency(LogEntry.objects.all(), 5)

    assert timedelta(days=8, hours=23).total_seconds() == pytest.approx(currency.expires_in.total_seconds(), abs=0.1)

    assert (datetime.now(tz=UTC) + timedelta(days=8)).date() == currency.expires_on
    assert CurrencyStatus.EXPIRING == currency.status
    assert 5 == currency.landings_to_renew


def test_lowest_currency_status():
    assert CurrencyStatus.CURRENT == min(CurrencyStatus.CURRENT, CurrencyStatus.CURRENT)
    assert CurrencyStatus.EXPIRING == min(CurrencyStatus.CURRENT, CurrencyStatus.EXPIRING)
    assert CurrencyStatus.NOT_CURRENT == min(CurrencyStatus.EXPIRING, CurrencyStatus.NOT_CURRENT)
