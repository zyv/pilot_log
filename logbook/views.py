import datetime
from typing import Iterable

from django.http import HttpResponse
from django.shortcuts import render

from .models import Aircraft, AircraftType, LogEntry


def index(request):
    def compute_totals(entries: Iterable[LogEntry]):
        return {
            "time": sum(
                (entry.arrival_time - entry.departure_time for entry in entries),
                datetime.timedelta()
            ),
            "landings": sum(entry.landings for entry in entries)
        }

    return HttpResponse(render(request, "logbook/dashboard.html", {
        "totals": {
            aircraft_type: {
                **compute_totals(LogEntry.objects.filter(aircraft__type=aircraft_type.name)),
                **{
                    "per_aircraft":
                        [
                            (aircraft, compute_totals(LogEntry.objects.filter(aircraft=aircraft)))
                            for aircraft in Aircraft.objects.filter(type=aircraft_type.name)
                        ]
                }
            } for aircraft_type in AircraftType
        },
    }))
