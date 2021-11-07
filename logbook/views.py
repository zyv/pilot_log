import datetime
from typing import Iterable

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import QuerySet
from django.urls import reverse_lazy
from django.views import generic

from .models import Aircraft, AircraftType, Certificate, FunctionType, LogEntry


class AuthenticatedListView(UserPassesTestMixin, LoginRequiredMixin, generic.ListView):
    login_url = reverse_lazy("admin:login")

    def test_func(self):
        return self.request.user.is_staff


class DashboardView(AuthenticatedListView):
    queryset = AircraftType
    template_name = "logbook/dashboard.html"

    @staticmethod
    def compute_totals(entries: Iterable[LogEntry]):
        return {
            "time": sum((entry.arrival_time - entry.departure_time for entry in entries), datetime.timedelta()),
            "landings": sum(entry.landings for entry in entries),
        }

    def get_context_data(self, *args, **kwargs):
        def totals_per_function(log_entries: QuerySet):
            return {
                function.name: self.compute_totals(log_entries.filter(time_function=function.name))
                for function in FunctionType
            }

        return {
            "totals_per_type": {
                aircraft_type: {
                    **self.compute_totals(LogEntry.objects.filter(aircraft__type=aircraft_type.name)),
                    **{"per_function": totals_per_function(LogEntry.objects.filter(aircraft__type=aircraft_type.name))},
                    **{
                        "per_aircraft": [
                            (
                                aircraft,
                                totals_per_function(LogEntry.objects.filter(aircraft=aircraft)),
                                self.compute_totals(LogEntry.objects.filter(aircraft=aircraft)),
                            )
                            for aircraft in Aircraft.objects.filter(type=aircraft_type.name)
                        ],
                    },
                }
                for aircraft_type in self.queryset
            },
            "grand_total": self.compute_totals(LogEntry.objects.all()),
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
