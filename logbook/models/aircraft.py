from typing import Optional

from django.db import models

from logbook.statistics.currency import NinetyDaysCurrency, get_ninety_days_currency


class AircraftType(models.TextChoices):
    GLD = "GLD", "Glider"
    TMG = "TMG", "Touring Motor Glider"
    SEP = "SEP", "Single Engine Piston"


class SpeedUnit(models.TextChoices):
    KMH = "KMH", "km/h"
    KT = "KT", "kt"
    MPH = "MPH", "mph"


class Aircraft(models.Model):
    type = models.CharField(max_length=3, choices=AircraftType.choices)
    maker = models.CharField(max_length=64)
    model = models.CharField(max_length=64)

    # https://www.icao.int/publications/doc8643/pages/search.aspx
    icao_designator = models.CharField(max_length=4)

    registration = models.CharField(max_length=9, unique=True)

    currency_required = models.BooleanField(default=False)

    speed_unit = models.CharField(max_length=3, choices=SpeedUnit.choices)

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
    v_s = models.PositiveSmallIntegerField(verbose_name="Vs", help_text="Stall speed", blank=True, null=True)
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
    def currency_status(self) -> Optional[NinetyDaysCurrency]:
        from .log_entry import LogEntry

        return get_ninety_days_currency(LogEntry.objects.filter(aircraft=self)) if self.currency_required else None
