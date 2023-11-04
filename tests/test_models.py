from datetime import UTC, datetime, timedelta

from django.test import TestCase

from logbook.models import Certificate


class ModelsTest(TestCase):
    def test_certificate_valid(self):
        certificate_old = Certificate.objects.create(
            name="Test",
            issue_date=datetime.now(tz=UTC),
        )
        certificate_new = Certificate.objects.create(
            name="Test",
            issue_date=datetime.now(tz=UTC),
            supersedes=certificate_old,
        )

        self.assertFalse(certificate_old.valid)
        self.assertTrue(certificate_new.valid)
        self.assertEqual(certificate_new, certificate_old.superseded_by)

        certificate_new.valid_until = (datetime.now(tz=UTC) - timedelta(days=1)).date()
        self.assertFalse(certificate_new.valid)
