from datetime import date
from enum import Enum

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, F, Q
from django_countries.fields import CountryField


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


class Aerodrome(models.Model):
    name = models.CharField(max_length=75)
    city = models.CharField(max_length=75)
    country = CountryField()
    icao_code = models.CharField(max_length=4)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    elevation = models.IntegerField()
    priority = models.IntegerField()

    def __str__(self):
        return f"{self.icao_code} ({self.name})"

    class Meta:
        ordering = ("priority",)


class Aircraft(models.Model):
    type = models.CharField(max_length=3, choices=[(at.name, at.value) for at in AircraftType])
    maker = models.CharField(max_length=64)
    model = models.CharField(max_length=64)

    # https://www.icao.int/publications/doc8643/pages/search.aspx
    icao_designator = models.CharField(max_length=4)

    registration = models.CharField(max_length=9, unique=True)

    def __str__(self):
        return f"{self.registration} ({self.maker} {self.model})"

    class Meta:
        ordering = ("registration",)
        verbose_name_plural = "aircraft"


class Pilot(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ("last_name",)
        unique_together = ("first_name", "last_name")


class LogEntry(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT)

    from_aerodrome = models.ForeignKey(Aerodrome, on_delete=models.PROTECT, related_name="from_aerodrome_set")
    to_aerodrome = models.ForeignKey(Aerodrome, on_delete=models.PROTECT, related_name="to_aerodrome_set")

    departure_time = models.DateTimeField(unique=True)
    arrival_time = models.DateTimeField(unique=True)

    landings = models.PositiveSmallIntegerField(default=1)

    time_function = models.CharField(max_length=5, choices=[(ft.name, ft.value) for ft in FunctionType])

    pilot = models.ForeignKey(Pilot, on_delete=models.PROTECT, related_name="pilot_set")
    copilot = models.ForeignKey(Pilot, on_delete=models.PROTECT, related_name="copilot_set", blank=True, null=True)

    launch_type = models.CharField(max_length=5, blank=True, choices=[(lt.name, lt.value) for lt in LaunchType])

    remarks = models.CharField(max_length=255, blank=True)

    cross_country = models.BooleanField(default=False)
    night = models.BooleanField(default=False)

    slots = models.PositiveSmallIntegerField(default=1, help_text="Number of logbook slots for this entry.")

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
            f"{self.pilot.last_name} / {self.copilot.last_name} "
            f"{'[XC] ' if self.cross_country else ''}"
            f"{'[N] ' if self.night else ''}"
            f"{remarks}".strip()
        )

    def clean(self):
        # Check constraints can't reference other tables; it's possible via UDFs, but not universally supported by RDBs
        if (
            self.aircraft_id is not None  # checks if foreign key is set to avoid `RelatedObjectDoesNotExist` exception!
            and self.aircraft.type == AircraftType.GLD.name
            and not self.launch_type
        ):
            raise ValidationError("Launch type is required for gliders!")

    class Meta:
        constraints = (
            CheckConstraint(check=Q(arrival_time__gt=F("departure_time")), name="arrival_after_departure"),
            CheckConstraint(check=~Q(copilot=F("pilot")), name="copilot_not_pilot"),
            CheckConstraint(
                check=(
                    Q(time_function=FunctionType.PIC.name)  # PIC time may be XC or not XC
                    | ~Q(time_function=FunctionType.PIC.name) & Q(cross_country=False)  # non-PIC time must be non-XC
                ),
                name="no_pic_no_xc",
            ),
        )
        ordering = ("-arrival_time",)
        verbose_name_plural = "Log entries"


class Certificate(models.Model):
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=255, blank=True)
    issue_date = models.DateField()
    valid_until = models.DateField(blank=True, null=True)
    authority = models.CharField(max_length=255)
    remarks = models.CharField(max_length=255, blank=True)

    @property
    def is_valid(self) -> bool:
        return self.valid_until is None or self.valid_until >= date.today()

    def __str__(self):
        return f"{self.name}{' ({})'.format(self.number) if self.number else ''}"

    class Meta:
        ordering = ("name", "-valid_until")
