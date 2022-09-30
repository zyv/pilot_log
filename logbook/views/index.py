from django.db.models import QuerySet

from ..models import Aircraft, AircraftType, FunctionType, LogEntry
from .utils import AuthenticatedListView, compute_totals


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
        }
