from datetime import UTC, datetime, timedelta

from django.test import TestCase

from logbook.models import Certificate


class ModelsTest(TestCase):
    def test_is_valid(self):
        certificate = Certificate.objects.create(name="Test", issue_date=datetime.now(tz=UTC))
        self.assertTrue(certificate.is_valid)

        certificate.valid_until = (datetime.now(tz=UTC) - timedelta(days=1)).date()
        self.assertFalse(certificate.is_valid)

        certificate.relinquished = True
        certificate.valid_until = None
        self.assertFalse(certificate.is_valid)
