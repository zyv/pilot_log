from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.db.models import QuerySet

from ..models import FunctionType, LogEntry
from .utils import (
    CPL_START_DATE,
    PPL_END_DATE,
    PPL_START_DATE,
    AuthenticatedTemplateView,
    ExperienceRecord,
    TotalsRecord,
    compute_totals,
)


@dataclass(frozen=True, kw_only=True)
class ExperienceRequirements:
    experience: dict[str, ExperienceRecord]
    details: Optional[str] = None


class ExperienceIndexView(AuthenticatedTemplateView):
    template_name = "logbook/experience_list.html"

    def get_context_data(self, **kwargs):
        log_entries = LogEntry.objects.filter(departure_time__gte=PPL_START_DATE)
        return super().get_context_data(**kwargs) | {
            "ppl": get_ppl_experience(log_entries.filter(departure_time__lt=PPL_END_DATE)),
            "night": get_night_experience(log_entries.filter(night=True)),
            "ir": get_ir_experience(log_entries),
            "cpl": get_cpl_experience(log_entries),
        }


def get_ppl_experience(log_entries: QuerySet) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "Dual instruction": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=25), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL.name)),
            ),
            "Supervised solo": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=10), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name)),
            ),
            "Cross-country solo": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=5), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name, cross_country=True)),
            ),
            "Total hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=45), landings=0),
                accrued=compute_totals(log_entries),
            ),
        },
        details="""
                Solo cross-country flight time must include at least 1 cross-country flight of at least 270 km (150 NM),
                during which full stop landings at 2 aerodromes different from the aerodrome of departure shall be made.
                """,
    )


def get_night_experience(log_entries: QuerySet) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "Solo full-stop landings": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=0), landings=5),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name), full_stop=True),
            ),
            "Dual instruction": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=3), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL.name)),
            ),
            "Dual cross-country (>27 NM)": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=1), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL.name, cross_country=True)),
            ),
            "Total hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=5), landings=0),
                accrued=compute_totals(log_entries),
            ),
        },
    )


def get_ir_experience(log_entries: QuerySet) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "Cross-country PIC": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=50), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name, cross_country=True)),
            ),
        },
    )


def get_cpl_experience(log_entries: QuerySet) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={  # TODO: add dual
            "PIC": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=100), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name)),
            ),
            "Cross-country PIC": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=20), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name, cross_country=True)),
            ),
            "Visual dual instruction": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=15), landings=0),
                accrued=compute_totals(
                    log_entries.filter(time_function=FunctionType.DUAL.name, departure_time__gte=CPL_START_DATE),
                ),
            ),
            "Total hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=200), landings=0),
                accrued=compute_totals(log_entries),
            ),
        },
        details="""
                PIC time shall include a VFR crosscountry flight of at least 540 km (300 NM), in the course of which
                full stop landings at two aerodromes different from the aerodrome of departure shall be made.
                Additionally, NVFR and IR (or instrument flight instruction) are required. At least 5 hours of the
                flight instruction shall be carried out in an aeroplane certificated for the carriage of at least
                4 persons and have a variable pitch propeller and retractable landing gear.
                """,
    )
