from dataclasses import dataclass
from datetime import timedelta

from django.db.models import QuerySet

from ..models import Certificate, FunctionType, LogEntry
from .utils import PPL_END_DATE, PPL_START_DATE, AuthenticatedListView, TotalsRecord, compute_totals


@dataclass
class ExperienceRecord:
    required: TotalsRecord
    accrued: TotalsRecord

    @property
    def remaining(self) -> TotalsRecord:
        remaining = self.required - self.accrued
        if remaining.time.total_seconds() < 0:
            remaining.time = timedelta(0)
        if remaining.landings < 0:
            remaining.landings = 0
        return remaining


class CertificateIndexView(AuthenticatedListView):
    model = Certificate

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(*args, **kwargs) | {
            "ppl": get_ppl_experience(
                LogEntry.objects.filter(departure_time__gte=PPL_START_DATE, departure_time__lt=PPL_END_DATE),
            ),
        }


def get_ppl_experience(log_entries: QuerySet) -> dict:
    """
    https://www.easa.europa.eu/sites/default/files/dfu/Part-FCL.pdf

    (a) Applicants for a PPL(A) shall have completed at least 45 hours of flight instruction in aeroplanes or TMGs,
        5 of which may have been completed in an FSTD, including at least:
    (1) 25 hours of dual flight instruction; and
    (2) 10 hours of supervised solo flight time, including at least 5 hours of solo cross-country flight time
        with at least 1 cross-country flight of at least 270 km (150 NM), during which full stop landings
        at 2 aerodromes different from the aerodrome of departure shall be made.
    """
    return {
        "Dual instruction": ExperienceRecord(
            required=TotalsRecord(time=timedelta(hours=25), landings=1),
            accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL.name)),
        ),
        "Supervised solo": ExperienceRecord(
            required=TotalsRecord(time=timedelta(hours=10), landings=1),
            accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name)),
        ),
        "Cross-country solo": ExperienceRecord(
            required=TotalsRecord(time=timedelta(hours=5), landings=1),
            accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name, cross_country=True)),
        ),
        "Total hours": ExperienceRecord(
            required=TotalsRecord(time=timedelta(hours=45), landings=1),
            accrued=compute_totals(log_entries),
        ),
    }
