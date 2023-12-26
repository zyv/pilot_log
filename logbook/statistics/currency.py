from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import OuterRef, QuerySet, Subquery, Sum, Value

if TYPE_CHECKING:
    from ..models.log_entry import LogEntry


class CurrencyStatus(models.TextChoices):
    CURRENT = "🟢"
    EXPIRING = "🟡"
    NOT_CURRENT = "🔴"


@dataclass(frozen=True, kw_only=True)
class NinetyDaysCurrency:
    status: CurrencyStatus
    expires_in: timedelta
    landings_to_renew: int

    @property
    def expires_on(self) -> date:
        return datetime.now(tz=UTC).date() + self.expires_in


CURRENCY_REQUIRED_LANDINGS_PASSENGER = 3
CURRENCY_REQUIRED_LANDINGS_NIGHT = 1
CURRENCY_DAYS_RANGE = 90
CURRENCY_DAYS_WARNING = 30


def get_ninety_days_currency(
    queryset: QuerySet["LogEntry"],
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
