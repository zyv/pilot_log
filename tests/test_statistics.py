from datetime import UTC, datetime, timedelta

import pytest

from logbook.models.log_entry import LogEntry
from logbook.statistics.currency import CurrencyStatus, get_rolling_currency
from logbook.statistics.experience import compute_totals

from .conftest import NUMBER_OF_LOG_ENTRIES


@pytest.mark.django_db
def test_compute_totals_total_landings(log_entries):
    totals = compute_totals(log_entries)
    assert totals.landings == NUMBER_OF_LOG_ENTRIES + 2


@pytest.mark.django_db
def test_compute_totals_full_stop_landings(log_entries):
    totals = compute_totals(log_entries, full_stop=True)
    assert totals.landings == NUMBER_OF_LOG_ENTRIES


@pytest.mark.django_db
def test_compute_totals_time(log_entries):
    totals = compute_totals(log_entries)
    assert totals.time.total_seconds() == pytest.approx(
        (timedelta(minutes=1) * NUMBER_OF_LOG_ENTRIES).total_seconds(), abs=0.1
    )


@pytest.mark.django_db
def test_not_current():  # no fixture!
    currency = get_rolling_currency(LogEntry.objects.all(), 5)

    assert currency.expires_in == timedelta(days=0)
    assert currency.expires_on == datetime.now(tz=UTC).date()
    assert currency.status == CurrencyStatus.NOT_CURRENT
    assert currency.landings_to_renew == 5


@pytest.mark.django_db
def test_current_linear(log_entries):
    currency = get_rolling_currency(log_entries, 5)

    assert currency.expires_in.total_seconds() == pytest.approx(timedelta(days=5).total_seconds(), abs=0.1)
    assert currency.expires_on == (datetime.now(tz=UTC) + timedelta(days=5 - 1)).date()
    assert currency.status == CurrencyStatus.EXPIRING
    assert currency.landings_to_renew == 1


@pytest.mark.django_db
def test_current_first_current_and_expired_on_same_day(log_entries):
    first_current_entry = LogEntry.objects.get(pk=NUMBER_OF_LOG_ENTRIES)
    first_current_entry.pk = None
    first_current_entry.landings = 7
    first_current_entry.departure_time -= timedelta(hours=1)
    first_current_entry.arrival_time -= timedelta(hours=1)
    first_current_entry.save()

    currency = get_rolling_currency(log_entries, 5)

    assert currency.expires_in.total_seconds() == pytest.approx(timedelta(days=8, hours=23).total_seconds(), abs=0.1)
    assert currency.expires_on == (datetime.now(tz=UTC) + timedelta(days=8)).date()
    assert currency.status == CurrencyStatus.EXPIRING
    assert currency.landings_to_renew == 5


def test_lowest_currency_status():
    assert min(CurrencyStatus.CURRENT, CurrencyStatus.CURRENT) == CurrencyStatus.CURRENT
    assert min(CurrencyStatus.CURRENT, CurrencyStatus.EXPIRING) == CurrencyStatus.EXPIRING
    assert min(CurrencyStatus.EXPIRING, CurrencyStatus.NOT_CURRENT) == CurrencyStatus.NOT_CURRENT
