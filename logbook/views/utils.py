import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView

from ..models import LogEntry

PPL_START_DATE = datetime(2021, 12, 1, 0, 0, tzinfo=timezone.utc)
PPL_END_DATE = datetime(2022, 1, 29, 0, 0, tzinfo=timezone.utc)


@dataclass(frozen=True, kw_only=True)
class TotalsRecord:
    time: timedelta
    landings: int

    def __sub__(self, other: "TotalsRecord") -> "TotalsRecord":
        return TotalsRecord(time=self.time - other.time, landings=self.landings - other.landings)


@dataclass(frozen=True, kw_only=True)
class ExperienceRecord:
    required: TotalsRecord
    accrued: TotalsRecord

    @property
    def remaining(self) -> TotalsRecord:
        remaining = self.required - self.accrued

        if remaining.time.total_seconds() < 0:
            remaining = dataclasses.replace(remaining, time=timedelta())

        if remaining.landings < 0:
            remaining = dataclasses.replace(remaining, landings=0)

        return remaining

    @property
    def completed(self) -> bool:
        return self.remaining.time.total_seconds() == 0 and self.remaining.landings == 0


def compute_totals(entries: Iterable[LogEntry]) -> TotalsRecord:
    return TotalsRecord(
        time=sum((entry.arrival_time - entry.departure_time for entry in entries), timedelta()),
        landings=sum(entry.landings for entry in entries),
    )


class AuthenticatedView(UserPassesTestMixin, LoginRequiredMixin):
    login_url = reverse_lazy("admin:login")

    def test_func(self):
        return self.request.user.is_staff


class AuthenticatedTemplateView(AuthenticatedView, TemplateView):
    pass


class AuthenticatedListView(AuthenticatedView, ListView):
    pass
