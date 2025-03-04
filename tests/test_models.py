from datetime import UTC, datetime, timedelta

import pytest

from logbook.models.pilot import Certificate


@pytest.mark.django_db
def test_certificate_valid():
    certificate_old = Certificate.objects.create(
        name="Test",
        issue_date=datetime.now(tz=UTC),
    )
    certificate_new = Certificate.objects.create(
        name="Test",
        issue_date=datetime.now(tz=UTC),
        supersedes=certificate_old,
    )

    assert not certificate_old.valid
    assert certificate_new.valid
    assert certificate_old.superseded_by == certificate_new

    certificate_new.valid_until = (datetime.now(tz=UTC) - timedelta(days=1)).date()
    assert not certificate_new.valid
