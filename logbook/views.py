import datetime
from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import QuerySet
from django.urls import reverse_lazy
from django.views import generic

from .models import Aircraft, AircraftType, Certificate, FunctionType, LogEntry
from .templatetags.logbook_utils import duration

PPL_START_DATE = datetime.datetime(2021, 12, 1, 0, 0, tzinfo=datetime.timezone.utc)


@dataclass
class TotalsRecord:
    time: datetime.timedelta
    landings: int

    @property
    def zero(self):
        return self.time.total_seconds() == 0 and self.landings == 0

    def __sub__(self, other: "TotalsRecord") -> "TotalsRecord":
        return TotalsRecord(time=self.time - other.time, landings=self.landings - other.landings)

    def __str__(self):
        return duration(self.time, "%{h}h %{m}m") + f", {self.landings} landing{'s' if self.landings >1 else ''}"


@dataclass
class ExperienceRecord:
    required: TotalsRecord
    accrued: TotalsRecord

    @property
    def remaining(self) -> TotalsRecord:
        remaining = self.required - self.accrued
        if remaining.time.total_seconds() < 0:
            remaining.time = 0
        if remaining.landings < 0:
            remaining.landings = 0
        return remaining


class AuthenticatedListView(UserPassesTestMixin, LoginRequiredMixin, generic.ListView):
    login_url = reverse_lazy("admin:login")

    def test_func(self):
        return self.request.user.is_staff


def compute_totals(entries: Iterable[LogEntry]) -> TotalsRecord:
    return TotalsRecord(
        time=sum((entry.arrival_time - entry.departure_time for entry in entries), datetime.timedelta()),
        landings=sum(entry.landings for entry in entries),
    )


class DashboardView(AuthenticatedListView):
    queryset = AircraftType
    template_name = "logbook/dashboard.html"

    def get_context_data(self, *args, **kwargs):
        def totals_per_function(log_entries: QuerySet):
            return {
                function.name: compute_totals(log_entries.filter(time_function=function.name))
                for function in FunctionType
            }

        return {
            "totals_per_type": {
                aircraft_type: {
                    "grand": compute_totals(LogEntry.objects.filter(aircraft__type=aircraft_type.name)),
                    **{"per_function": totals_per_function(LogEntry.objects.filter(aircraft__type=aircraft_type.name))},
                    **{
                        "per_aircraft": [
                            (
                                aircraft,
                                totals_per_function(LogEntry.objects.filter(aircraft=aircraft)),
                                compute_totals(LogEntry.objects.filter(aircraft=aircraft)),
                            )
                            for aircraft in Aircraft.objects.filter(type=aircraft_type.name)
                        ],
                    },
                }
                for aircraft_type in self.queryset
            },
            "grand_total": compute_totals(LogEntry.objects.all()),
            "ppl": get_ppl_experience(LogEntry.objects.filter(departure_time__gte=PPL_START_DATE)),
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
            required=TotalsRecord(time=datetime.timedelta(hours=25), landings=1),
            accrued=compute_totals(log_entries.filter(time_function=FunctionType.DUAL.name)),
        ),
        "Supervised solo": ExperienceRecord(
            required=TotalsRecord(time=datetime.timedelta(hours=10), landings=1),
            accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name)),
        ),
        "Cross-country": ExperienceRecord(
            required=TotalsRecord(time=datetime.timedelta(hours=5), landings=1),
            accrued=compute_totals(log_entries.filter(time_function=FunctionType.PIC.name, cross_country=True)),
        ),
        "Total hours": ExperienceRecord(
            required=TotalsRecord(time=datetime.timedelta(hours=45), landings=1),
            accrued=compute_totals(log_entries),
        ),
    }


class EntryIndexView(AuthenticatedListView):
    model = LogEntry
    ordering = "arrival_time"
    paginate_by = 7

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(*args, **kwargs) | {
            "aircraft_types": list(AircraftType),
            "function_types": list(FunctionType),
        }

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(
            queryset,
            page_size,
            orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty(),
        )

        # Set last page as a default to mimic paper logbook
        if not self.request.GET.get(self.page_kwarg):
            self.kwargs[self.page_kwarg] = paginator.num_pages

        return super().paginate_queryset(queryset, page_size)


class CertificateIndexView(AuthenticatedListView):
    model = Certificate
