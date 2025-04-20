from typing import TYPE_CHECKING, Optional

from colorfield.fields import ColorField
from django.db import models
from django.utils.functional import classproperty

if TYPE_CHECKING:
    from ..statistics.currency import RollingCurrency


class AircraftType(models.TextChoices):
    GLD = "GLD", "Glider"
    TMG = "TMG", "Touring Motor Glider"
    SEP = "SEP", "Single Engine Piston"

    @classproperty
    def gliders(cls) -> tuple["AircraftType", ...]:
        return cls.GLD, cls.TMG

    @classproperty
    def powered(cls) -> tuple["AircraftType", ...]:
        return cls.TMG, cls.SEP

    @classproperty
    def airplanes(cls) -> tuple["AircraftType", ...]:
        return (cls.SEP,)


class SpeedUnit(models.TextChoices):
    KMH = "KMH", "km/h"
    KT = "KT", "kt"
    MPH = "MPH", "mph"


class FuelType(models.Model):
    name = models.CharField(max_length=64)
    color = ColorField(default="#00FFFF")
    density = models.FloatField(help_text="Density in kg/L")

    class Meta:
        ordering = ("-density",)

    def __str__(self):
        return self.name


class Aircraft(models.Model):
    CURRENCY_REQUIRED_LANDINGS = 3

    type = models.CharField(max_length=3, choices=AircraftType.choices)
    maker = models.CharField(max_length=64)
    model = models.CharField(max_length=64)

    # https://www.icao.int/publications/doc8643/pages/search.aspx
    icao_designator = models.CharField(max_length=4)

    registration = models.CharField(max_length=9, unique=True)

    currency_required = models.BooleanField(default=False)

    night_vfr = models.BooleanField(default=False, help_text="Certified for Night VFR")

    reduced_noise = models.BooleanField(default=False, help_text="Erhöhter Schallschutz")

    speed_unit = models.CharField(max_length=3, choices=SpeedUnit.choices)

    fuel_types = models.ManyToManyField(FuelType)

    v_r = models.PositiveSmallIntegerField(verbose_name="Vr", help_text="Rotation speed", blank=True, null=True)
    v_y = models.PositiveSmallIntegerField(
        verbose_name="Vy",
        help_text="Best rate of climb speed",
        blank=True,
        null=True,
    )
    v_bg = models.PositiveSmallIntegerField(verbose_name="Vbg", help_text="Best glide speed", blank=True, null=True)
    v_app = models.PositiveSmallIntegerField(verbose_name="Vapp", help_text="Approach speed", blank=True, null=True)
    v_ref = models.PositiveSmallIntegerField(
        verbose_name="Vref",
        help_text="Uncorrected final approach speed",
        blank=True,
        null=True,
    )
    v_s1 = models.PositiveSmallIntegerField(verbose_name="Vs1", help_text="Stall speed (clean)", blank=True, null=True)
    v_fe = models.PositiveSmallIntegerField(verbose_name="Vfe", help_text="Flap extension speed", blank=True, null=True)
    v_c = models.PositiveSmallIntegerField(verbose_name="Vc", help_text="Cruise speed", blank=True, null=True)

    demonstrated_crosswind = models.PositiveSmallIntegerField(
        help_text="Demonstrated crosswind in KT",
        blank=True,
        null=True,
    )

    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ("registration",)
        verbose_name_plural = "aircraft"

    def __str__(self):
        return f"{self.registration} ({self.maker} {self.model})"

    @property
    def currency_status(self) -> Optional["RollingCurrency"]:
        from ..statistics.currency import get_rolling_currency

        return (
            get_rolling_currency(self.logentry_set.all(), self.CURRENCY_REQUIRED_LANDINGS)
            if self.currency_required
            else None
        )
