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
            f"{remarks}"
        )

    def clean(self):
        if self.aircraft.type == AircraftType.GLD.name and not self.launch_type:
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

    def __str__(self):
        return f"{self.name}{' ({})'.format(self.number) if self.number else ''}"

    class Meta:
        ordering = ("name",)


"""
# Currency requirements

## SEP rating

1. Pass a proficiency check in a single-engine (single-pilot) aeroplane with an examiner. The proficiency check must
   take place within the 3 months immediately before the rating’s expiry date; or
2. 12 hours of flight time in single-engine (single-pilot) aeroplane within the 12 months preceding the rating's expiry
   date, including the following:
  a. 6 hours as pilot-in-command (PIC)
  b. 12 take-offs and landings
  c. a training flight of at least 1 hour (or a maximum of three totalling 1 hour) with the same flight instructor or
     class rating instructor.

## Passenger

### FCL.060 - Recent experience

b. Aeroplanes, helicopters, powered-lift, airships and sailplanes. A pilot shall not operate an aircraft in commercial
   air transport or carrying passengers:
  1. as PIC or co-pilot unless he/she has carried out, in the preceding 90 days, at least 3 take- offs, approaches and
     landings in an aircraft of the same type or class or an FFS representing that type or class. The 3 take-offs and
     landings shall be performed in either multi-pilot or single-pilot operations, depending on the privileges held by
     the pilot; and
  2. as PIC at night unless he/she:
    i. has carried out in the preceding 90 days at least 1 take-off, approach and landing at night as a pilot flying in
       an aircraft of the same type or class or an FFS representing that type or class; or
    ii. holds an IR;

## ICAO English language proficiency

* Level 1-3: not for operational use
* Level 4: 4 years
* Level 5: 6 years
* Level 6: unlimited

## Medical II

If you are under 40, the certificate will be valid for 60 months. Please note that if you are issued with a Class 2
medical before you reach 40, it will no longer be valid once you reach 42 years of age.

If you are aged between 40 and 50 the certificate will be valid for 24 months. Please note that if you are issued
with a Class 2 medical before you reach 50, it will no longer be valid once you reach 51 years of age.

If you are aged 50 or over the certificate will be valid for 12 months.
"""
