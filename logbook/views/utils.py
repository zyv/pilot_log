import dataclasses
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Iterable, Optional

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import OuterRef, QuerySet, Subquery, Sum, Value
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView

from ..models import LogEntry

PPL_START_DATE = datetime(2021, 12, 1, 0, 0, tzinfo=UTC)
PPL_END_DATE = datetime(2022, 1, 29, 0, 0, tzinfo=UTC)
CPL_START_DATE = datetime.now(tz=UTC)


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


@dataclass(frozen=True, kw_only=True)
class ExperienceRequirements:
    experience: dict[str, ExperienceRecord]
    details: Optional[str] = None


def compute_totals(entries: Iterable[LogEntry], full_stop=False) -> TotalsRecord:
    return TotalsRecord(
        time=sum((entry.arrival_time - entry.departure_time for entry in entries), timedelta()),
        landings=sum(entry.landings if not full_stop else 1 for entry in entries),
    )


class CurrencyStatus(StrEnum):
    CURRENT = "🟢"
    EXPIRING = "🟡"
    NOT_CURRENT = "🔴"


@dataclass(frozen=True, kw_only=True)
class NinetyDaysCurrency:
    status: CurrencyStatus
    expires_in: timedelta
    landings_to_renew: int


CURRENCY_REQUIRED_LANDINGS_PASSENGER = 3
CURRENCY_REQUIRED_LANDINGS_NIGHT = 1

CURRENCY_DAYS_RANGE = 90
CURRENCY_DAYS_WARNING = 14


def get_ninety_days_currency(
    queryset: QuerySet[LogEntry],
    required_landings: int = CURRENCY_REQUIRED_LANDINGS_PASSENGER,
) -> NinetyDaysCurrency:
    eligible_entries = queryset.filter(arrival_time__gte=datetime.now(tz=UTC) - timedelta(days=CURRENCY_DAYS_RANGE))

    annotated_entries = eligible_entries.annotate(
        eligible_landings=Subquery(
            eligible_entries.filter(arrival_time__gte=OuterRef("arrival_time"))
            .annotate(remove_group_by=Value(None))
            .values("remove_group_by")
            .annotate(total_landings_until=Sum("landings"))
            .values("total_landings_until"),
        ),
    )

    first_current_entry = (
        annotated_entries.filter(eligible_landings__gte=required_landings).order_by("eligible_landings").first()
    )

    first_expired_entry = (
        annotated_entries.filter(eligible_landings__lt=required_landings).order_by("-eligible_landings").first()
    )

    time_to_expiry = (
        timedelta(days=CURRENCY_DAYS_RANGE) - (datetime.now(tz=UTC) - first_current_entry.arrival_time)
        if first_current_entry is not None
        else timedelta(days=0)
    )

    landings_to_renew = required_landings - (
        first_expired_entry.eligible_landings if first_expired_entry is not None else 0
    )

    currency_status = (
        CurrencyStatus.NOT_CURRENT
        if first_current_entry is None
        else (
            CurrencyStatus.EXPIRING
            if time_to_expiry <= timedelta(days=CURRENCY_DAYS_WARNING)
            else CurrencyStatus.CURRENT
        )
    )

    return NinetyDaysCurrency(
        status=currency_status,
        expires_in=time_to_expiry,
        landings_to_renew=landings_to_renew,
    )


class AuthenticatedView(UserPassesTestMixin, LoginRequiredMixin):
    login_url = reverse_lazy("admin:login")

    def test_func(self):
        return self.request.user.is_staff


class AuthenticatedTemplateView(AuthenticatedView, TemplateView):
    pass


class AuthenticatedListView(AuthenticatedView, ListView):
    pass
