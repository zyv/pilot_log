from datetime import UTC, datetime
from typing import Optional

from django.db import models
from django.db.models import CheckConstraint, F, Q, UniqueConstraint


class Pilot(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=150)

    me = models.BooleanField(default=False)

    class Meta:
        constraints = (
            UniqueConstraint(
                fields=["me"],
                condition=Q(me=True),
                name="only_one_me",
            ),
        )
        ordering = ("last_name",)
        unique_together = ("first_name", "last_name")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Certificate(models.Model):
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=255, blank=True)
    issue_date = models.DateField()
    valid_until = models.DateField(blank=True, null=True)
    authority = models.CharField(max_length=255)
    remarks = models.CharField(max_length=255, blank=True)
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="supersedes_set",
    )

    class Meta:
        constraints = (
            CheckConstraint(
                check=Q(valid_until__isnull=True) | Q(valid_until__gt=F("issue_date")),
                name="validity_after_issue",
            ),
            CheckConstraint(
                check=~Q(id=F("supersedes")),
                name="supersedes_self",
            ),
            UniqueConstraint(
                fields=["supersedes"],
                condition=Q(supersedes__isnull=False),
                name="supersedes_unique",
            ),
        )
        ordering = ("name", F("supersedes").desc(nulls_last=True), "-valid_until")

    def __str__(self):
        return f"{self.name}{' / {}'.format(self.number) if self.number else ''} ({self.issue_date})"

    @property
    def valid(self) -> bool:
        return (
            self.valid_until is None or self.valid_until >= datetime.now(tz=UTC).date()
        ) and not self.supersedes_set.count()

    @property
    def superseded_by(self) -> Optional["Certificate"]:
        return self.supersedes_set.first()
