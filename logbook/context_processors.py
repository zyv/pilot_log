from .models import AircraftType, FunctionType, LaunchType, SpeedUnit
from .statistics.currency import CurrencyStatus


def enums(_):
    return {
        enum.__name__: enum
        for enum in [
            AircraftType,
            FunctionType,
            LaunchType,
            SpeedUnit,
            CurrencyStatus,
        ]
    }
