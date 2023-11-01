from datetime import UTC, datetime, time, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import QuerySet
from django.utils.timezone import make_aware

from ..models import AircraftType, Certificate, FunctionType, LogEntry
from ..statistics.experience import (
    ExperienceRecord,
    ExperienceRequirements,
    TotalsRecord,
    compute_totals,
)
from .utils import (
    AuthenticatedTemplateView,
)


class ExperienceIndexView(AuthenticatedTemplateView):
    template_name = "logbook/experience_list.html"

    def get_context_data(self, **kwargs):
        log_entries = LogEntry.objects.filter(departure_time__gte=settings.PPL_START_DATE)
        return super().get_context_data(**kwargs) | {
            "sep_revalidation": get_sep_revalidation_experience(log_entries),
            "ppl": get_ppl_experience(log_entries.filter(departure_time__lt=settings.PPL_END_DATE)),
            "night": get_night_experience(log_entries.filter(night=True)),
            "ir": get_ir_experience(log_entries),
            "cpl": get_cpl_experience(log_entries),
        }


def get_sep_revalidation_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    eligible_entries = log_entries.filter(
        aircraft__type__in={AircraftType.SEP, AircraftType.TMG},
        departure_time__gte=make_aware(
            datetime.combine(
                Certificate.objects.get(name__contains="SEP").valid_until - relativedelta(months=12),
                time.min,
            ),
            UTC,
        ),
    )
    return ExperienceRequirements(
        experience={
            "12 hours of flight time": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=12), landings=0),
                accrued=compute_totals(eligible_entries),
            ),
            "6 hours as PIC": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=6), landings=0),
                accrued=compute_totals(eligible_entries.filter(time_function=FunctionType.PIC)),
            ),
            "12 take-offs and 12 landings": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=0), landings=12),
                accrued=compute_totals(eligible_entries),
            ),
            "Refresher training with FI or CRI": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=1), landings=0),
                accrued=compute_totals(eligible_entries.filter(time_function=FunctionType.DUAL)),
            ),
        },
        details="""
                Refresher training of at least 1 hour of total flight time with a flight instructor (FI)
                or a class rating instructor (CRI).
                """,
    )


def get_ppl_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "Dual instruction": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=25), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL)),
            ),
            "Supervised solo": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=10), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC)),
            ),
            "Cross-country solo": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=5), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC, cross_country=True)),
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


def get_night_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "Solo full-stop landings": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=0), landings=5),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC), full_stop=True),
            ),
            "Dual instruction": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=3), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL)),
            ),
            "Dual cross-country (>27 NM)": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=1), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL, cross_country=True)),
            ),
            "Total hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=5), landings=0),
                accrued=compute_totals(log_entries),
            ),
        },
    )


def get_ir_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "Cross-country PIC": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=50), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC, cross_country=True)),
            ),
        },
    )


def get_cpl_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={  # TODO: add dual
            "PIC": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=100), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC)),
            ),
            "Cross-country PIC": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=20), landings=0),
                accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC, cross_country=True)),
            ),
            "Visual dual instruction": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=15), landings=0),
                accrued=compute_totals(
                    log_entries.filter(time_function=FunctionType.DUAL, departure_time__gte=settings.CPL_START_DATE),
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
