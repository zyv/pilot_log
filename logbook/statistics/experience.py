import dataclasses
from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Sum

from ..models.aircraft import AircraftType
from ..models.log_entry import LogEntry, LogEntryQuerySet


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
    details: str | None = None


def total_time(entries: LogEntryQuerySet[LogEntry]) -> timedelta:
    duration_sum = entries.with_durations().aggregate(Sum("duration"))["duration__sum"]
    return duration_sum if duration_sum is not None else timedelta()


def total_landings(entries: LogEntryQuerySet[LogEntry], full_stop: bool) -> int:
    landings = entries.aggregate(Sum("landings"))["landings__sum"] if not full_stop else entries.count()
    return landings if landings is not None else 0


def compute_totals(entries: LogEntryQuerySet[LogEntry], full_stop=False) -> TotalsRecord:
    return TotalsRecord(time=total_time(entries), landings=total_landings(entries, full_stop))


MAX_GLIDER_CPL_ENTRY_CREDIT = timedelta(hours=10)
MAX_GLIDER_CPL_ISSUE_CREDIT = timedelta(hours=30)


def cpl_total_hours_requirements(entries: LogEntryQuerySet[LogEntry], glider_credit: timedelta) -> TotalsRecord:
    glider_time = total_time(entries.filter(aircraft__type__in=AircraftType.gliders))
    if glider_time > glider_credit:
        glider_time = glider_credit

    airplane_time = total_time(entries.filter(aircraft__type__in=AircraftType.airplanes))

    return TotalsRecord(
        time=airplane_time + glider_time,
        landings=0,
    )
