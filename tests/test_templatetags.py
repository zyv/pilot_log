from datetime import UTC, datetime, timedelta

import pytest
from django.template import TemplateSyntaxError
from django.utils.safestring import SafeString

from logbook.models.aircraft import AircraftType, SpeedUnit
from logbook.models.log_entry import FunctionType
from logbook.statistics.experience import ExperienceRecord, TotalsRecord
from logbook.templatetags.logbook_utils import duration, replace, represent, subtract, to_kt, total_landings, total_time

from .conftest import DAYS_IN_THE_PAST, EXTRA_LANDINGS, NUMBER_OF_LOG_ENTRIES


def test_represent():
    totals1 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=1)
    totals2 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=2)
    experience1 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=3), accrued=totals1)
    experience2 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=0), accrued=totals1)
    experience3 = ExperienceRecord(required=TotalsRecord(time=timedelta(0), landings=1), accrued=totals1)

    assert represent(totals1, experience1) == "50h 30m, 1 landing"
    assert represent(totals2, experience1) == "50h 30m, 2 landings"
    assert represent(totals1, experience2) == "50h 30m"
    assert represent(totals1, experience3) == "1 landing"


def test_subtract():
    assert 3 == subtract(5, 2)


def test_replace_result():
    result = replace("Hello, world!", "world", "morning")

    assert result == "Hello, morning!"
    assert isinstance(result, SafeString)


def test_replace_non_str_value():
    assert replace(100, "world", "morning") is None


def test_replace_non_str_args():
    with pytest.raises(TemplateSyntaxError):
        replace("Hello, world!", 5, 7)

    with pytest.raises(TemplateSyntaxError):
        replace("Hello, world!", "foo", 7)

    with pytest.raises(TemplateSyntaxError):
        replace("Hello, world!", 5, "bar")


def test_to_kt():
    assert to_kt(100, SpeedUnit.KMH) == 54
    assert to_kt(100, SpeedUnit.MPH) == 87
    assert to_kt(100, SpeedUnit.KT) == 100

    with pytest.raises(TemplateSyntaxError):
        to_kt(100, "foo")


def test_duration():
    assert duration(timedelta(days=1, hours=2, minutes=3, seconds=4), "%H:%M") == "26:03"
    assert duration(timedelta(days=1, hours=2, minutes=3, seconds=4), "%d:%h:%s") == "1:2:184"


@pytest.mark.django_db
def test_total_time(log_entries):
    time = total_time(datetime.now(tz=UTC))
    assert time == "0:30"

    time = total_time(datetime.now(tz=UTC), time_function=FunctionType.DUAL)
    assert time == "0:00"

    time = total_time(datetime.now(tz=UTC), aircraft_type=AircraftType.GLD)
    assert time == "0:00"


@pytest.mark.django_db
def test_total_landings(log_entries):
    landings = total_landings(datetime.now(tz=UTC))
    assert landings == str(NUMBER_OF_LOG_ENTRIES + EXTRA_LANDINGS)

    landings = total_landings(datetime.now(tz=UTC) - timedelta(days=DAYS_IN_THE_PAST - NUMBER_OF_LOG_ENTRIES / 2))
    assert landings == str(NUMBER_OF_LOG_ENTRIES // 2 + EXTRA_LANDINGS)
