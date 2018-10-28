import datetime
from typing import Iterable

from django.views import generic

from .models import Aircraft, AircraftType, LogEntry


class DashboardView(generic.ListView):
    queryset = AircraftType
    template_name = "logbook/dashboard.html"

    @staticmethod
    def compute_totals(entries: Iterable[LogEntry]):
        return {
            "time": sum(
                (entry.arrival_time - entry.departure_time for entry in entries),
                datetime.timedelta()
            ),
            "landings": sum(entry.landings for entry in entries)
        }

    def get_context_data(self, *args, **kwargs):
        return {
            "totals": {
                aircraft_type: {
                    **self.compute_totals(LogEntry.objects.filter(aircraft__type=aircraft_type.name)),
                    **{
                        "per_aircraft":
                            [
                                (aircraft, self.compute_totals(LogEntry.objects.filter(aircraft=aircraft)))
                                for aircraft in Aircraft.objects.filter(type=aircraft_type.name)
                            ]
                    }
                } for aircraft_type in self.queryset
            },
        }
