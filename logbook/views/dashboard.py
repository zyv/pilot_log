from datetime import UTC, datetime, timedelta

from django.db.models import QuerySet

from ..models.aircraft import Aircraft, AircraftType
from ..models.log_entry import FunctionType, LogEntry
from ..statistics.currency import CURRENCY_REQUIRED_LANDINGS_NIGHT, get_ninety_days_currency
from ..statistics.experience import compute_totals
from .utils import (
    AuthenticatedTemplateView,
    check_certificates_expiry,
)


class DashboardView(AuthenticatedTemplateView):
    template_name = "logbook/dashboard.html"

    def get(self, request, *args, **kwargs):
        check_certificates_expiry(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        def totals_per_function(log_entries: QuerySet[LogEntry]):
            return {function: compute_totals(log_entries.filter(time_function=function)) for function in FunctionType}

        now = datetime.now(tz=UTC)
        periods = {
            "1M": timedelta(days=30),
            "6M": timedelta(days=180),
            "1Y": timedelta(days=365),
            "2Y": timedelta(days=365 * 2),
        }
        return super().get_context_data(*args, **kwargs) | {
            "passenger_currency": {
                "sep": {
                    "day": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.SEP,
                        ),
                    ),
                    "night": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.SEP,
                            night=True,
                        ),
                        required_landings=CURRENCY_REQUIRED_LANDINGS_NIGHT,
                    ),
                },
                "tmg": {
                    "day": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.TMG,
                        ),
                    ),
                    "night": get_ninety_days_currency(
                        LogEntry.objects.filter(
                            aircraft__type=AircraftType.TMG,
                            night=True,
                        ),
                        required_landings=CURRENCY_REQUIRED_LANDINGS_NIGHT,
                    ),
                },
            },
            "totals_per_type": {
                aircraft_type: {
                    "grand": compute_totals(LogEntry.objects.filter(aircraft__type=aircraft_type)),
                    "per_function": totals_per_function(LogEntry.objects.filter(aircraft__type=aircraft_type)),
                    "per_aircraft": [
                        (
                            aircraft,
                            totals_per_function(LogEntry.objects.filter(aircraft=aircraft)),
                            compute_totals(LogEntry.objects.filter(aircraft=aircraft)),
                        )
                        for aircraft in Aircraft.objects.filter(type=aircraft_type)
                    ],
                    "per_period": [
                        {
                            "per_function": totals_per_function(
                                LogEntry.objects.filter(
                                    aircraft__type=aircraft_type,
                                    departure_time__gt=now - period_delta,
                                ),
                            ),
                            "grand": compute_totals(
                                LogEntry.objects.filter(
                                    aircraft__type=aircraft_type,
                                    departure_time__gt=now - period_delta,
                                ),
                            ),
                        }
                        for period_delta in periods.values()
                    ],
                }
                for aircraft_type in reversed(AircraftType)
            },
            "grand_total": compute_totals(LogEntry.objects.all()),
            "period_labels": list(periods.keys()),
        }
