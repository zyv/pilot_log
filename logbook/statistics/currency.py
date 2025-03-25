from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models import OuterRef, QuerySet, Subquery, Sum, Value

from ..models.log_entry import FunctionType, LogEntry


class CurrencyStatus(models.TextChoices):
    CURRENT = "<!-- Priority: 3 --><i class='fa-solid fa-circle text-success'></i>"
    EXPIRING = "<!-- Priority: 2 --><i class='fa-solid fa-circle text-warning'></i>"
    NOT_CURRENT = "<!-- Priority: 1 --><i class='fa-solid fa-circle text-danger'></i>"


@dataclass(frozen=True, kw_only=True)
class RollingCurrency:
    status: CurrencyStatus
    expires_in: timedelta
    landings_to_renew: int
    time_to_renew: timedelta | None = None
    comment: str | None = None

    @property
    def expires_on(self) -> date:
        return datetime.now(tz=UTC).date() + self.expires_in


CURRENCY_TIME_RANGE_NINETY = timedelta(days=90)
CURRENCY_TIME_RANGE_LAPL = relativedelta(years=2)
CURRENCY_TIME_RANGE_WARNING = timedelta(days=30)

CURRENCY_REQUIRED_LANDINGS_PASSENGER = 3
CURRENCY_REQUIRED_LANDINGS_NIGHT = 1

CURRENCY_REQUIRED_LANDINGS_LAPL = 12
CURRENCY_REQUIRED_TIME_TOTAL_LAPL = timedelta(hours=12)
CURRENCY_REQUIRED_TIME_REFRESHER_LAPL = timedelta(hours=1)


def get_time_to_expiry(currency_time_range: timedelta, reference_entry: LogEntry) -> timedelta:
    return (
        currency_time_range - (datetime.now(tz=UTC) - reference_entry.departure_time)
        if reference_entry is not None
        else timedelta(0)
    )


def get_currency_status(expires_in: timedelta, reference_entry: LogEntry) -> CurrencyStatus:
    return (
        CurrencyStatus.NOT_CURRENT
        if reference_entry is None
        else CurrencyStatus.EXPIRING
        if expires_in <= CURRENCY_TIME_RANGE_WARNING
        else CurrencyStatus.CURRENT
    )


def get_rolling_currency(
    queryset: QuerySet["LogEntry"],
    required_landings: int,
    required_time: timedelta | None = None,
    currency_time_range: timedelta = CURRENCY_TIME_RANGE_NINETY,
) -> RollingCurrency:
    eligible_entries = queryset.filter(departure_time__gte=datetime.now(tz=UTC) - currency_time_range)

    annotated_entries = eligible_entries.annotate(
        eligible_landings=Subquery(
            eligible_entries.filter(departure_time__gte=OuterRef("departure_time"))
            .annotate(remove_group_by=Value(None))
            .values("remove_group_by")
            .annotate(total_landings_until=Sum("landings"))
            .values("total_landings_until"),
        ),
        eligible_time=Subquery(
            eligible_entries.filter(departure_time__gte=OuterRef("departure_time"))
            .with_durations()
            .annotate(remove_group_by=Value(None))
            .values("remove_group_by")
            .annotate(total_time_until=Sum("duration"))
            .values("total_time_until"),
        ),
    )

    current_entries = annotated_entries.filter(eligible_landings__gte=required_landings).order_by("eligible_landings")

    if required_time is not None:
        current_entries = current_entries.filter(eligible_time__gte=required_time).order_by("eligible_time")

    first_current_entry = current_entries.first()

    # It only makes sense to consider expired entries from the day after the first day of currency, because otherwise
    # a wrong number of landings to renew will be reported if currency is established through two flights on the same
    # day - see tests for an example when this matters
    departure_date_filter = (
        {"departure_time__date__gt": first_current_entry.departure_time.date()}
        if first_current_entry is not None
        else {}
    )

    expired_entries = annotated_entries.filter(
        **(
            {"eligible_landings__lt": required_landings}
            | ({"eligible_time__lt": required_time} if required_time is not None else {})
            | departure_date_filter
        ),
    ).order_by("-eligible_landings", "-eligible_time")

    first_expired_entry = expired_entries.first()

    expires_in = get_time_to_expiry(currency_time_range, first_current_entry)

    landings_to_renew = required_landings - (
        first_expired_entry.eligible_landings if first_expired_entry is not None else 0
    )

    time_to_renew = (
        required_time - (first_expired_entry.eligible_time if first_expired_entry is not None else timedelta(0))
        if required_time is not None
        else None
    )

    return RollingCurrency(
        status=get_currency_status(expires_in, first_current_entry),
        expires_in=expires_in,
        landings_to_renew=landings_to_renew,
        time_to_renew=time_to_renew,
    )


def get_passenger_currency(entries: QuerySet["LogEntry"]) -> (RollingCurrency, RollingCurrency):
    day_currency = get_rolling_currency(entries, CURRENCY_REQUIRED_LANDINGS_PASSENGER)

    night_currency = get_rolling_currency(entries.filter(night=True), CURRENCY_REQUIRED_LANDINGS_NIGHT)

    if day_currency.status == CurrencyStatus.NOT_CURRENT:
        night_currency = day_currency

    return day_currency, night_currency


def get_lapl_currency(entries: QuerySet["LogEntry"]) -> RollingCurrency:
    flight_time_currency = get_rolling_currency(
        entries,
        required_landings=CURRENCY_REQUIRED_LANDINGS_LAPL,
        required_time=CURRENCY_REQUIRED_TIME_TOTAL_LAPL,
        currency_time_range=CURRENCY_TIME_RANGE_LAPL,
    )

    refresher_training = (
        entries.with_durations()
        .filter(time_function=FunctionType.DUAL, duration__gte=CURRENCY_REQUIRED_TIME_REFRESHER_LAPL)
        .first()
    )

    refresher_training_expires_in = get_time_to_expiry(CURRENCY_TIME_RANGE_LAPL, refresher_training)
    refresher_training_currency_status = get_currency_status(refresher_training_expires_in, refresher_training)

    resulting_currency = RollingCurrency(
        status=min(flight_time_currency.status, refresher_training_currency_status),
        expires_in=(
            flight_time_currency.expires_in
            if flight_time_currency.expires_in < refresher_training_expires_in
            else refresher_training_expires_in
        ),
        landings_to_renew=flight_time_currency.landings_to_renew,
        time_to_renew=flight_time_currency.time_to_renew,
        comment=(
            "expiry limited by refresher training"
            if flight_time_currency.expires_in > refresher_training_expires_in
            else None
        ),
    )

    return resulting_currency
