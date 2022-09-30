from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView

from ..models import LogEntry
from ..templatetags.logbook_utils import duration

PPL_START_DATE = datetime(2021, 12, 1, 0, 0, tzinfo=timezone.utc)
PPL_END_DATE = datetime(2022, 1, 29, 0, 0, tzinfo=timezone.utc)


@dataclass
class TotalsRecord:
    time: timedelta
    landings: int

    @property
    def zero(self):
        return self.time.total_seconds() == 0 and self.landings == 0

    def __sub__(self, other: "TotalsRecord") -> "TotalsRecord":
        return TotalsRecord(time=self.time - other.time, landings=self.landings - other.landings)

    def __str__(self):
        return duration(self.time, "%{h}h %{m}m").replace(" 0m", "")


def compute_totals(entries: Iterable[LogEntry]) -> TotalsRecord:
    return TotalsRecord(
        time=sum((entry.arrival_time - entry.departure_time for entry in entries), timedelta()),
        landings=sum(entry.landings for entry in entries),
    )


class AuthenticatedListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    login_url = reverse_lazy("admin:login")

    def test_func(self):
        return self.request.user.is_staff
