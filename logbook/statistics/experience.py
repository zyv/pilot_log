import dataclasses
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Optional

from ..models.aircraft import AircraftType
from ..models.log_entry import FunctionType, LogEntry


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


def flight_time(entries: Iterable["LogEntry"]) -> timedelta:
    return sum((entry.arrival_time - entry.departure_time for entry in entries), timedelta())


def compute_totals(entries: Iterable["LogEntry"], full_stop=False) -> TotalsRecord:
    return TotalsRecord(
        time=flight_time(entries),
        landings=sum(entry.landings if not full_stop else 1 for entry in entries),
    )


def cpl_entry_requirements(entries: Iterable["LogEntry"]):
    max_glider_credit = timedelta(hours=10)
    glider_time = flight_time(
        entries.filter(time_function=FunctionType.PIC, aircraft__type__in=(AircraftType.GLD, AircraftType.TMG)),
    )
    if glider_time > max_glider_credit:
        glider_time = max_glider_credit

    airplane_time = flight_time(entries.filter(aircraft__type=AircraftType.SEP))

    return TotalsRecord(
        time=airplane_time + glider_time,
        landings=0,
    )
