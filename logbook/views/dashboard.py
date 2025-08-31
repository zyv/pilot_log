from datetime import UTC, datetime, timedelta

from django.db.models import QuerySet

from ..models.aircraft import Aircraft, AircraftType
from ..models.log_entry import FunctionType, LogEntry
from ..statistics.currency import get_lapl_currency, get_passenger_currency
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
            "3M": timedelta(days=30 * 3),
            "6M": timedelta(days=30 * 6),
            "9M": timedelta(days=30 * 9),
            "1Y": timedelta(days=365),
            "2Y": timedelta(days=365 * 2),
            "3Y": timedelta(days=365 * 3),
        }

        all_entries = LogEntry.objects.all()

        day_sep_currency, night_sep_currency = get_passenger_currency(
            all_entries.filter(aircraft__type=AircraftType.SEP),
        )
        day_tmg_currency, night_tmg_currency = get_passenger_currency(
            all_entries.filter(aircraft__type=AircraftType.TMG),
        )

        lapl_a_currency = get_lapl_currency(all_entries.filter(aircraft__type__in=AircraftType.powered))

        return super().get_context_data(*args, **kwargs) | {
            "lapl_a_currency": lapl_a_currency,
            "passenger_currency": {
                "sep": {
                    "day": day_sep_currency,
                    "night": night_sep_currency,
                },
                "tmg": {
                    "day": day_tmg_currency,
                    "night": night_tmg_currency,
                },
            },
            "totals_per_type": {
                aircraft_type: {
                    "grand": compute_totals(all_entries.filter(aircraft__type=aircraft_type)),
                    "per_function": totals_per_function(all_entries.filter(aircraft__type=aircraft_type)),
                    "per_aircraft": sorted(
                        (
                            (
                                aircraft,
                                totals_per_function(all_entries.filter(aircraft=aircraft)),
                                compute_totals(all_entries.filter(aircraft=aircraft)),
                            )
                            for aircraft in Aircraft.objects.filter(type=aircraft_type)
                        ),
                        key=lambda item: (
                            (-item[2].landings, -item[2].time)
                            if "-landings" in self.request.GET.get("order_by", "")
                            else (-item[2].time, -item[2].landings)
                            if "-time" in self.request.GET.get("order_by", "")
                            # Neutral element to preserve default sorting order
                            else 0
                        ),
                    ),
                    "per_period": [
                        {
                            "per_function": totals_per_function(
                                all_entries.filter(aircraft__type=aircraft_type, departure_time__gt=now - period_delta),
                            ),
                            "grand": compute_totals(
                                all_entries.filter(aircraft__type=aircraft_type, departure_time__gt=now - period_delta),
                            ),
                        }
                        for period_delta in periods.values()
                    ],
                }
                for aircraft_type in reversed(AircraftType)
            },
            "grand_total": compute_totals(all_entries),
            "period_labels": list(periods.keys()),
        }
