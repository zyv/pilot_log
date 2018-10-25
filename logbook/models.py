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
    registration = models.CharField(max_length=8, unique=True)

    def __str__(self):
        return f"{self.registration} ({self.model})"

    class Meta:
        ordering = ("registration",)


class Pilot(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ("last_name",)
        unique_together = ("first_name", "last_name")


# TODO: auto-populate from database, plus free text
AERODROME_CHOICES = (
    ("EDKA", "EDKA"),
    ("EDRV", "EDRV"),
)


class LogEntry(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT)

    from_aerodrome = models.CharField(max_length=64, choices=AERODROME_CHOICES)
    to_aerodrome = models.CharField(max_length=64, choices=AERODROME_CHOICES)

    # TODO: add complex constraints
    # https://docs.djangoproject.com/en/dev/ref/models/options/#django.db.models.Options.constraints
    departure_time = models.DateTimeField(unique=True)
    arrival_time = models.DateTimeField(unique=True)

    landings = models.PositiveSmallIntegerField(default=1)

    time_function = models.CharField(max_length=5, choices=[(ft.name, ft.value) for ft in FunctionType])

    # TODO: add complex constraints
    pilot = models.ForeignKey(Pilot, on_delete=models.PROTECT, related_name="pilot_set")
    copilot = models.ForeignKey(Pilot, on_delete=models.PROTECT, related_name="copilot_set", blank=True, null=True)

    launch_type = models.CharField(max_length=5, blank=True, choices=[(lt.name, lt.value) for lt in LaunchType])

    remarks = models.CharField(max_length=255, blank=True)

    # TODO: add cross-country flag?

    def __str__(self):
        duration = (self.arrival_time - self.departure_time).total_seconds()
        duration_hours = int(duration // 3600)
        duration_minutes = int((duration - duration_hours * 3600) // 60)
        remarks = f"({self.launch_type})" if self.launch_type else ""
        return (
            f"{self.departure_time.strftime('%Y-%m-%d %H:%M')} - {self.arrival_time.strftime('%H:%M')} "
            f"({duration_hours:02}:{duration_minutes:02}) "
            f"{self.aircraft.registration} ({self.aircraft.type}) "
            f"{self.from_aerodrome} -> {self.to_aerodrome} "
            f"{self.pilot.last_name} / {self.copilot.last_name} "
            f"{remarks}"
        )

    class Meta:
        ordering = ("-arrival_time",)
        verbose_name_plural = "Log entries"
