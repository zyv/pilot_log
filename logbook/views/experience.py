from datetime import UTC, datetime, time, timedelta

from django.conf import settings
from django.db.models import QuerySet
from django.utils.timezone import make_aware

from ..models.aircraft import AircraftType
from ..models.log_entry import FunctionType, LogEntry
from ..statistics.currency import CURRENCY_REQUIRED_TIME_REFRESHER_SEP, CURRENCY_TIME_RANGE_SEP
from ..statistics.experience import (
    MAX_GLIDER_CPL_ENTRY_CREDIT,
    MAX_GLIDER_CPL_ISSUE_CREDIT,
    ExperienceRecord,
    ExperienceRequirements,
    TotalsRecord,
    compute_totals,
    cpl_total_hours_requirements,
)
from .utils import (
    AuthenticatedTemplateView,
    get_current_sep_rating,
)


class ExperienceIndexView(AuthenticatedTemplateView):
    template_name = "logbook/experience_list.html"

    def get_context_data(self, **kwargs):
        log_entries = LogEntry.objects.all()
        return super().get_context_data(**kwargs) | {
            "total": get_total_experience(log_entries),
            "sep_revalidation": get_sep_revalidation_experience(
                log_entries.filter(departure_time__gte=settings.PPL_END_DATE)
            ),
            "ppl": get_ppl_experience(
                log_entries.filter(
                    departure_time__gte=settings.PPL_START_DATE, departure_time__lt=settings.PPL_END_DATE
                )
            ),
            "night": get_night_experience(log_entries.filter(night=True)),
            "ir": get_ir_experience(log_entries),
            "cpl": get_cpl_experience(log_entries),
            "cri": get_cri_experience(log_entries),
        }


def get_total_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "After PPL Skill Test": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=0), landings=0),
                accrued=compute_totals(log_entries.filter(departure_time__gt=settings.PPL_END_DATE)),
            ),
        },
    )


def get_sep_revalidation_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    eligible_entries = log_entries.filter(
        aircraft__type__in=AircraftType.powered,
        departure_time__gte=make_aware(
            datetime.combine(
                get_current_sep_rating().valid_until - CURRENCY_TIME_RANGE_SEP,
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
                accrued=compute_totals(
                    eligible_entries.filter(time_function=FunctionType.DUAL)
                    .with_durations()
                    .filter(duration__gte=CURRENCY_REQUIRED_TIME_REFRESHER_SEP)
                ),
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
            "Entry: Cross-country PIC hours (powered)": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=50), landings=0),
                accrued=compute_totals(
                    log_entries.filter(
                        time_function=FunctionType.PIC,
                        aircraft__type__in=AircraftType.powered,
                        cross_country=True,
                    )
                ),
            ),
            "Entry: Cross-country PIC hours (airplane)": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=10), landings=0),
                accrued=compute_totals(
                    log_entries.filter(
                        time_function=FunctionType.PIC,
                        aircraft__type__in=AircraftType.airplanes,
                        cross_country=True,
                    )
                ),
            ),
        },
        details="""
            PIC XC is to be completed in aeroplanes, TMGs, helicopters or airships, of which at least 10 hours shall be
            in the relevant aircraft category.
        """,
    )


def get_cpl_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "Entry: PIC hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=50), landings=0),
                accrued=compute_totals(
                    log_entries.filter(
                        time_function=FunctionType.PIC,
                        aircraft__type__in=AircraftType.airplanes,
                    )
                ),
            ),
            "Entry: Cross-country PIC hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=10), landings=0),
                accrued=compute_totals(
                    log_entries.filter(
                        time_function=FunctionType.PIC,
                        aircraft__type__in=AircraftType.airplanes,
                        cross_country=True,
                    )
                ),
            ),
            "Entry: Total hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=150), landings=0),
                accrued=cpl_total_hours_requirements(log_entries, MAX_GLIDER_CPL_ENTRY_CREDIT),
            ),
            "Issue: PIC hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=100), landings=0),
                accrued=compute_totals(
                    log_entries.filter(
                        time_function=FunctionType.PIC,
                        aircraft__type__in=AircraftType.airplanes,
                    ),
                ),
            ),
            "Issue: Cross-country PIC hours (incl. qualifying)": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=20), landings=0),
                accrued=compute_totals(
                    log_entries.filter(
                        time_function=FunctionType.PIC,
                        aircraft__type__in=AircraftType.airplanes,
                        cross_country=True,
                    ),
                ),
            ),
            "Issue: Total hours": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=200), landings=0),
                accrued=cpl_total_hours_requirements(log_entries, MAX_GLIDER_CPL_ISSUE_CREDIT),
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


def get_cri_experience(log_entries: QuerySet[LogEntry]) -> ExperienceRequirements:
    return ExperienceRequirements(
        experience={
            "(1) 300 hours flight time as a pilot on aeroplanes": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=300), landings=0),
                accrued=compute_totals(log_entries.filter(aircraft__type__in=AircraftType.powered)),
            ),
            "(2) TMG - 30 hours as PIC on the applicable class or type of aeroplane": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=30), landings=0),
                accrued=compute_totals(
                    log_entries.filter(time_function=FunctionType.PIC, aircraft__type__in=AircraftType.TMG)
                ),
            ),
            "(2) SEP - 30 hours as PIC on the applicable class or type of aeroplane": ExperienceRecord(
                required=TotalsRecord(time=timedelta(hours=30), landings=0),
                accrued=compute_totals(
                    log_entries.filter(time_function=FunctionType.PIC, aircraft__type__in=AircraftType.SEP)
                ),
            ),
        },
        details="""
        FCL.905.CRI - restricted to the class or type of aeroplane in which the instructor assessment of competence was
        taken.
        """,
    )
