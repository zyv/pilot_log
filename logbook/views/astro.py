import enum
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cached_property
from pathlib import Path
from zoneinfo import ZoneInfo

from django import forms
from django.views.generic import FormView
from skyfield import almanac
from skyfield import api as sf_api
from timezonefinder import TimezoneFinder

from ..models.aerodrome import Aerodrome
from ..templatetags.logbook_utils import duration
from .utils import AuthenticatedTemplateView


class SkyfieldTwilight(enum.IntEnum):
    NIGHT = 0
    ASTRONOMICAL = 1
    NAUTICAL = 2
    CIVIL = 3
    DAY = 4


class SkyfieldLocation(enum.IntEnum):
    SUNSET = 0
    SUNRISE = 1


def round_to_nearest_minute(dt: datetime) -> datetime:
    return (dt + timedelta(seconds=30)).replace(second=0, microsecond=0)


class AerodromeForm(forms.Form):
    aerodrome = forms.CharField(
        label="Aerodrome ICAO code",
        min_length=4,
        max_length=4,
        widget=forms.TextInput(attrs={"placeholder": "EDKA"}),
    )

    def clean_aerodrome(self):
        try:
            return Aerodrome.objects.get(icao_code=self.cleaned_data["aerodrome"].upper())
        except Aerodrome.DoesNotExist:
            raise forms.ValidationError("Aerodrome not found")


@dataclass(frozen=True, kw_only=True)
class LocationData:
    aerodrome: Aerodrome
    timezone: ZoneInfo
    morning_twilight: datetime
    sunrise: datetime
    sunset: datetime
    evening_twilight: datetime

    @property
    def morning_twilight_duration(self) -> timedelta:
        return self.sunrise - self.morning_twilight

    @property
    def evening_twilight_duration(self) -> timedelta:
        return self.evening_twilight - self.sunset

    @property
    def utc_offset(self) -> str:
        utc_offset = self.timezone.utcoffset(datetime.now(tz=UTC))
        return "UTC" + ("-" if utc_offset.total_seconds() < 0 else "+") + duration(utc_offset, "%H:%M")


class AstroIndexView(AuthenticatedTemplateView, FormView):
    template_name = "logbook/astro.html"
    form_class = AerodromeForm

    @cached_property
    def timezone_finder(self):
        return TimezoneFinder()

    @cached_property
    def ephemeris(self):
        return sf_api.load_file(Path(__file__).parent.parent / "fixtures" / "data" / "de421.bsp")

    def form_valid(self, form):
        aerodrome = form.cleaned_data["aerodrome"]

        tz = self.timezone_finder.timezone_at(lng=float(aerodrome.longitude), lat=float(aerodrome.latitude))
        zi = ZoneInfo(tz)

        today_midnight = datetime.now(tz=zi).replace(hour=0, minute=0, second=0, microsecond=0)

        timescale = sf_api.load.timescale()
        t0 = timescale.from_datetime(today_midnight)
        t1 = timescale.from_datetime(today_midnight + timedelta(days=1))

        location = sf_api.wgs84.latlon(aerodrome.latitude, aerodrome.longitude)

        find_discrete = almanac.find_discrete(t0, t1, almanac.sunrise_sunset(self.ephemeris, location))
        (sunrise_time, sunset_time), ss_events = find_discrete

        assert tuple(ss_events) == (SkyfieldLocation.SUNRISE, SkyfieldLocation.SUNSET)

        find_discrete = almanac.find_discrete(t0, t1, almanac.dark_twilight_day(self.ephemeris, location))
        twilight_times, twilight_events = find_discrete

        reference_events = [
            str(item)
            for item in (
                SkyfieldTwilight.NIGHT,
                SkyfieldTwilight.ASTRONOMICAL,
                SkyfieldTwilight.NAUTICAL,
                SkyfieldTwilight.CIVIL,
                SkyfieldTwilight.DAY,
                SkyfieldTwilight.CIVIL,
                SkyfieldTwilight.NAUTICAL,
                SkyfieldTwilight.ASTRONOMICAL,
            )
        ]

        assert "".join(map(str, twilight_events)) in "".join(reference_events + reference_events[::1])

        labeled_twilight_events = list(zip(twilight_times, twilight_events))

        def filter_first(label: SkyfieldTwilight, events: list[tuple[sf_api.Time, int]]):
            return next(filter(lambda event: event[1] == label, events))

        morning_twilight, _ = filter_first(SkyfieldTwilight.CIVIL, labeled_twilight_events)
        evening_twilight, _ = filter_first(SkyfieldTwilight.NAUTICAL, labeled_twilight_events[::-1])

        location_data = LocationData(
            aerodrome=aerodrome,
            timezone=zi,
            sunrise=round_to_nearest_minute(sunrise_time.utc_datetime()),
            sunset=round_to_nearest_minute(sunset_time.utc_datetime()),
            morning_twilight=round_to_nearest_minute(morning_twilight.utc_datetime()),
            evening_twilight=round_to_nearest_minute(evening_twilight.utc_datetime()),
        )

        return self.render_to_response(self.get_context_data(form=form, location_data=location_data))
