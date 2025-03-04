from datetime import timedelta

import pytest
from django.template import TemplateSyntaxError
from django.utils.safestring import SafeString

from logbook.models.aircraft import SpeedUnit
from logbook.statistics.experience import ExperienceRecord, TotalsRecord
from logbook.templatetags.logbook_utils import duration, replace, represent, subtract, to_kt


def test_represent():
    totals1 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=1)
    totals2 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=2)
    experience1 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=3), accrued=totals1)
    experience2 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=0), accrued=totals1)
    experience3 = ExperienceRecord(required=TotalsRecord(time=timedelta(0), landings=1), accrued=totals1)

    assert "50h 30m, 1 landing" == represent(totals1, experience1)
    assert "50h 30m, 2 landings" == represent(totals2, experience1)
    assert "50h 30m" == represent(totals1, experience2)
    assert "1 landing" == represent(totals1, experience3)


def test_subtract():
    assert 3 == subtract(5, 2)


def test_replace_result():
    result = replace("Hello, world!", "world", "morning")
    assert "Hello, morning!" == result
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
    assert 54 == to_kt(100, SpeedUnit.KMH)
    assert 87 == to_kt(100, SpeedUnit.MPH)
    assert 100 == to_kt(100, SpeedUnit.KT)

    with pytest.raises(TemplateSyntaxError):
        to_kt(100, "foo")


def test_duration():
    assert "26:03" == duration(timedelta(days=1, hours=2, minutes=3, seconds=4), "%H:%M")
    assert "1:2:184" == duration(timedelta(days=1, hours=2, minutes=3, seconds=4), "%d:%h:%s")
