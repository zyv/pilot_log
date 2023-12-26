from .models.aircraft import AircraftType, SpeedUnit
from .models.log_entry import FunctionType, LaunchType
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
