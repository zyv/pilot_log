from django.db.models import QuerySet

from ..models import Aircraft, AircraftType, FunctionType, LogEntry
from ..statistics.currency import CURRENCY_REQUIRED_LANDINGS_NIGHT, CurrencyStatus, get_ninety_days_currency
from ..statistics.experience import compute_totals
from .utils import (
    AuthenticatedListView,
)


class DashboardView(AuthenticatedListView):
    queryset = AircraftType
    template_name = "logbook/dashboard.html"

    def get_context_data(self, *args, **kwargs):
        def totals_per_function(log_entries: QuerySet[LogEntry]):
            return {
                function.name: compute_totals(log_entries.filter(time_function=function.name))
                for function in FunctionType
            }

        return super().get_context_data(*args, **kwargs) | {
            "CurrencyStatus": CurrencyStatus.__members__,
            "passenger_currency": {
                "sep": {
                    "day": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.SEP.name,
                            time_function=FunctionType.PIC.name,
                        ),
                    ),
                    "night": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.SEP.name,
                            time_function=FunctionType.PIC.name,
                            night=True,
                        ),
                        required_landings=CURRENCY_REQUIRED_LANDINGS_NIGHT,
                    ),
                },
                "tmg": {
                    "day": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.TMG.name,
                            time_function=FunctionType.PIC.name,
                        ),
                    ),
                    "night": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.TMG.name,
                            time_function=FunctionType.PIC.name,
                            night=True,
                        ),
                        required_landings=CURRENCY_REQUIRED_LANDINGS_NIGHT,
                    ),
                },
            },
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
