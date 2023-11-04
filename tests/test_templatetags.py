from datetime import timedelta
from unittest import TestCase

from django.template import TemplateSyntaxError
from django.utils.safestring import SafeString

from logbook.models import SpeedUnit
from logbook.statistics.experience import ExperienceRecord, TotalsRecord
from logbook.templatetags.logbook_utils import duration, replace, represent, subtract, to_kt


class TestRepresent(TestCase):
    def test_result(self):
        totals1 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=1)
        totals2 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=2)
        experience1 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=3), accrued=totals1)
        experience2 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=0), accrued=totals1)
        experience3 = ExperienceRecord(required=TotalsRecord(time=timedelta(0), landings=1), accrued=totals1)

        self.assertEqual("50h 30m, 1 landing", represent(totals1, experience1))
        self.assertEqual("50h 30m, 2 landings", represent(totals2, experience1))
        self.assertEqual("50h 30m", represent(totals1, experience2))
        self.assertEqual("1 landing", represent(totals1, experience3))


class TestSubtract(TestCase):
    def test_result(self):
        self.assertEqual(3, subtract(5, 2))


class TestReplace(TestCase):
    def test_result(self):
        result = replace("Hello, world!", "world", "morning")
        self.assertEqual("Hello, morning!", result)
        self.assertIsInstance(result, SafeString)

    def test_non_str_value(self):
        self.assertIsNone(replace(100, "world", "morning"))

    def test_non_str_args(self):
        self.assertRaises(TemplateSyntaxError, replace, "Hello, world!", 5, 7)
        self.assertRaises(TemplateSyntaxError, replace, "Hello, world!", "foo", 7)
        self.assertRaises(TemplateSyntaxError, replace, "Hello, world!", 5, "bar")


class TestToKT(TestCase):
    def test_to_kt(self):
        self.assertEqual(54, to_kt(100, SpeedUnit.KMH))
        self.assertEqual(87, to_kt(100, SpeedUnit.MPH))
        self.assertEqual(100, to_kt(100, SpeedUnit.KT))
        self.assertRaises(TemplateSyntaxError, to_kt, 100, "foo")


class TestDuration(TestCase):
    def test_duration(self):
        self.assertEqual("26:03", duration(timedelta(days=1, hours=2, minutes=3, seconds=4), "%H:%M"))
        self.assertEqual("1:2:184", duration(timedelta(days=1, hours=2, minutes=3, seconds=4), "%d:%h:%s"))
