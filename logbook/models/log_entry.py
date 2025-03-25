from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, DurationField, ExpressionWrapper, F, Q

from .aerodrome import Aerodrome
from .aircraft import Aircraft, AircraftType
from .pilot import Pilot


class FunctionType(models.TextChoices):
    PIC = "PIC", "Pilot-in-Command"
    DUAL = "DUAL", "Dual instruction time"


class LaunchType(models.TextChoices):
    SELF = "SELF", "Self-launch"
    WINCH = "WINCH", "Winch launch"
    TOW = "TOW", "Aerotow"


class LogEntryQuerySet(models.QuerySet):
    def with_durations(self):
        return self.annotate(
            duration=ExpressionWrapper(F("arrival_time") - F("departure_time"), output_field=DurationField())
        )


class LogEntry(models.Model):
    objects = LogEntryQuerySet.as_manager()

    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT)

    from_aerodrome = models.ForeignKey(Aerodrome, on_delete=models.PROTECT, related_name="from_aerodrome_set")
    to_aerodrome = models.ForeignKey(Aerodrome, on_delete=models.PROTECT, related_name="to_aerodrome_set")

    departure_time = models.DateTimeField(unique=True)
    arrival_time = models.DateTimeField(unique=True)

    landings = models.PositiveSmallIntegerField(default=1)

    time_function = models.CharField(max_length=5, choices=FunctionType.choices)

    pilot = models.ForeignKey(Pilot, on_delete=models.PROTECT, related_name="pilot_set")
    copilot = models.ForeignKey(Pilot, on_delete=models.PROTECT, related_name="copilot_set", blank=True, null=True)

    launch_type = models.CharField(max_length=5, blank=True, choices=LaunchType.choices)

    remarks = models.CharField(max_length=255, blank=True)

    cross_country = models.BooleanField(default=False)
    night = models.BooleanField(default=False)

    slots = models.PositiveSmallIntegerField(default=1, help_text="Number of logbook slots for this entry.")

    class Meta:
        constraints = (
            CheckConstraint(condition=Q(arrival_time__gt=F("departure_time")), name="arrival_after_departure"),
            CheckConstraint(condition=~Q(copilot=F("pilot")), name="copilot_not_pilot"),
            CheckConstraint(
                condition=(
                    Q(time_function=FunctionType.PIC)  # PIC time may be XC or not XC
                    | ~Q(time_function=FunctionType.PIC) & Q(cross_country=False)  # non-PIC time must be non-XC
                ),
                name="no_pic_no_xc",
            ),
        )
        ordering = ("-arrival_time",)
        verbose_name_plural = "Log entries"

    def __str__(self):
        duration = (self.arrival_time - self.departure_time).total_seconds()
        duration_hours = int(duration // 3600)
        duration_minutes = int((duration - duration_hours * 3600) // 60)
        remarks = f"({self.launch_type})" if self.launch_type else ""
        return (
            f"{self.departure_time.strftime('%Y-%m-%d %H:%M')} - {self.arrival_time.strftime('%H:%M')} "
            f"({duration_hours:02}:{duration_minutes:02}) "
            f"{self.aircraft.registration} ({self.aircraft.type}) "
            f"{self.from_aerodrome.icao_code} -> {self.to_aerodrome.icao_code} "
            f"{self.pilot.last_name}{' / ' + self.copilot.last_name if self.copilot is not None else ''} "
            f"{'[XC] ' if self.cross_country else ''}"
            f"{'[N] ' if self.night else ''}"
            f"{remarks}".strip()
        )

    def clean(self):
        # Check constraints can't reference other tables; it's possible via UDFs, but not universally supported by RDBs
        if (
            self.aircraft_id is not None  # checks if foreign key is set to avoid `RelatedObjectDoesNotExist` exception!
            and self.aircraft.type == AircraftType.GLD
            and not self.launch_type
        ):
            raise ValidationError("Launch type is required for gliders!")
