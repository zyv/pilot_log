from enum import Enum

from django.db import models


class AircraftType(Enum):
    GLD = "Glider"
    TMG = "Touring Motor Glider"
    SEP = "Single Engine Piston"


class FunctionType(Enum):
    PIC = "Pilot-in-Command"
    DUAL = "Dual instruction time"


class LaunchType(Enum):
    SELF = "Self-launch"
    WINCH = "Winch launch"
    TOW = "Aerotow"


class Aircraft(models.Model):
    type = models.CharField(max_length=3, choices=[(at.name, at.value) for at in AircraftType])
    model = models.CharField(max_length=64)
    registration = models.CharField(max_length=8)

    def __str__(self):
        return f"{self.registration} ({self.model})"


AERODROME_CHOICES = (
    ("EDKA", "EDKA"),
)

PILOT_CHOICES = (
    ("Yury Zaytsev", "Yury Zaytsev"),
    ("Bernd Orban", "Bernd Orban"),
)


class LogEntry(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT)

    from_aerodrome = models.CharField(max_length=64, choices=AERODROME_CHOICES)
    to_aerodrome = models.CharField(max_length=64, choices=AERODROME_CHOICES)

    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    time_function = models.CharField(max_length=5, choices=[(ft.name, ft.value) for ft in FunctionType])

    pilot = models.CharField(max_length=64, choices=PILOT_CHOICES)
    copilot = models.CharField(max_length=64, choices=PILOT_CHOICES)

    launch_type = models.CharField(max_length=5, blank=True, choices=[(lt.name, lt.value) for lt in LaunchType])

    remarks = models.CharField(max_length=255, blank=True)

    # cross-country

    def __str__(self):
        return f"{self.departure_time.date}"
