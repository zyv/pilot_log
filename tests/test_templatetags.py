from datetime import timedelta
from unittest import TestCase

from django.template import TemplateSyntaxError
from django.utils.safestring import SafeString

from logbook.models import SpeedUnit
from logbook.statistics.experience import ExperienceRecord, TotalsRecord
from logbook.templatetags.logbook_utils import replace, represent, subtract, to_kt


class TestRepresent(TestCase):
    def test_result(self):
        totals1 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=1)
        totals2 = TotalsRecord(time=timedelta(hours=50, minutes=30), landings=2)
        experience1 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=3), accrued=totals1)
        experience2 = ExperienceRecord(required=TotalsRecord(time=timedelta(hours=100), landings=0), accrued=totals1)
        experience3 = ExperienceRecord(required=TotalsRecord(time=timedelta(0), landings=1), accrued=totals1)

        self.assertEqual(represent(totals1, experience1), "50h 30m, 1 landing")
        self.assertEqual(represent(totals2, experience1), "50h 30m, 2 landings")
        self.assertEqual(represent(totals1, experience2), "50h 30m")
        self.assertEqual(represent(totals1, experience3), "1 landing")


class TestSubtract(TestCase):
    def test_result(self):
        self.assertEqual(subtract(5, 2), 3)


class TestReplace(TestCase):
    def test_result(self):
        result = replace("Hello, world!", "world", "morning")
        self.assertEqual(result, "Hello, morning!")
        self.assertIsInstance(result, SafeString)

    def test_non_str_value(self):
        self.assertIsNone(replace(100, "world", "morning"))

    def test_non_str_args(self):
        self.assertRaises(TemplateSyntaxError, replace, "Hello, world!", 5, 7)
        self.assertRaises(TemplateSyntaxError, replace, "Hello, world!", "foo", 7)
        self.assertRaises(TemplateSyntaxError, replace, "Hello, world!", 5, "bar")


class TestToKT(TestCase):
    def test_to_kt(self):
        self.assertEqual(to_kt(100, SpeedUnit.KMH), 54)
        self.assertEqual(to_kt(100, SpeedUnit.MPH), 87)
        self.assertEqual(to_kt(100, SpeedUnit.KT), 100)
        self.assertRaises(TemplateSyntaxError, to_kt, 100, "foo")
