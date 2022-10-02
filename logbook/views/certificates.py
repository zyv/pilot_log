from dataclasses import dataclass
from datetime import date, timedelta

from ..models import Certificate, FunctionType, LogEntry
from .utils import AuthenticatedListView, ExperienceRecord, ExperienceRequirements, TotalsRecord, compute_totals


@dataclass(frozen=True, kw_only=True)
class PassengerCurrency:
    day: ExperienceRequirements
    night: ExperienceRequirements


class CertificateIndexView(AuthenticatedListView):
    model = Certificate

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(*args, **kwargs) | {
            "passenger_currency": get_passenger_currency(),
        }


def get_passenger_currency() -> PassengerCurrency:
    return PassengerCurrency(
        day=ExperienceRequirements(
            experience={
                "Preceding 90 days": ExperienceRecord(
                    required=TotalsRecord(time=timedelta(hours=0), landings=3),
                    accrued=compute_totals(
                        LogEntry.objects.filter(
                            time_function=FunctionType.PIC.name,
                            departure_time__gte=date.today() - timedelta(days=90),
                        ),
                    ),
                ),
            },
            details="Same type or class required.",
        ),
        night=ExperienceRequirements(
            experience={
                "Preceding 90 days": ExperienceRecord(
                    required=TotalsRecord(time=timedelta(hours=0), landings=1),
                    accrued=compute_totals(
                        LogEntry.objects.filter(
                            time_function=FunctionType.PIC.name,
                            departure_time__gte=date.today() - timedelta(days=90),
                            night=True,
                        ),
                    ),
                ),
            },
            details="Waved if holding a current IR.",
        ),
    )
