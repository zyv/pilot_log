import datetime
from string import Template

from django import template
from django.template import TemplateSyntaxError
from django.utils.safestring import mark_safe
from django_filters import FilterSet

from ..models.aircraft import AircraftType, SpeedUnit
from ..models.log_entry import FunctionType, LogEntry
from ..statistics.experience import ExperienceRecord, TotalsRecord
from ..statistics.experience import total_landings as statistics_total_landings
from ..statistics.experience import total_time as statistics_total_time

register = template.Library()


class DurationTemplate(Template):
    delimiter = "%"


@register.filter
def duration(value: datetime.timedelta, format_specification: str = "%{h}h %{m}m"):
    duration_template = DurationTemplate(format_specification)

    days, remainder = divmod(value.total_seconds(), 24 * 60 * 60)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, seconds = divmod(remainder, 60)

    if "d" not in map(str.lower, duration_template.get_identifiers()):
        hours += days * 24

    if "h" not in map(str.lower, duration_template.get_identifiers()):
        minutes += hours * 60

    if "m" not in map(str.lower, duration_template.get_identifiers()):
        seconds += minutes * 60

    def pad(number: float) -> str:
        return f"{number:02.0f}"

    def ceil(number: float) -> str:
        return f"{number:.0f}"

    ds = {"d": days, "h": hours, "m": minutes, "s": seconds}
    substitutions = {k.upper(): pad(v) for k, v in ds.items()} | {k.lower(): ceil(v) for k, v in ds.items()}

    return duration_template.substitute(**substitutions)


@register.filter
def represent(total: TotalsRecord, experience: ExperienceRecord):
    """
    Represents **given** totals by using only the **requirements** from the experience record
    """
    time = duration(total.time, "%{h}h %{m}m").replace(" 0m", "")
    landings = "1 landing" if total.landings == 1 else f"{total.landings} landings"
    return ", ".join(
        ((time,) if experience.required.time else ()) + ((landings,) if experience.required.landings else ()),
    )


@register.filter
def subtract(value, argument):
    return value - argument


@register.simple_tag
def replace(value: str, old: str, new: str) -> str | None:
    if not all(isinstance(obj, str) for obj in (old, new)):
        raise TemplateSyntaxError("'replace' tag arguments must be strings")
    return mark_safe(value.replace(old, new)) if isinstance(value, str) else None


@register.filter
def to_kt(value: float, unit: SpeedUnit) -> int:
    match unit:
        case SpeedUnit.KMH:
            return round(value * 0.539957)
        case SpeedUnit.MPH:
            return round(value * 0.868976)
        case SpeedUnit.KT:
            return round(value)
        case _:
            raise TemplateSyntaxError(f"unknown speed unit: {unit}")


def get_filtered_entries(entries_filter: FilterSet | None):
    entries = LogEntry.objects.all()
    if entries_filter is not None and entries_filter.form.is_valid():
        entries = entries_filter.filter_queryset(entries)
    return entries


@register.simple_tag
def total_time(
    reference_time: datetime,
    time_function: FunctionType | None = None,
    aircraft_type: AircraftType | None = None,
    entries_filter: FilterSet | None = None,
) -> str:
    return duration(
        statistics_total_time(
            get_filtered_entries(entries_filter).filter(
                **{"arrival_time__lte": reference_time}
                | ({"time_function": time_function} if time_function is not None else {})
                | ({"aircraft__type": aircraft_type} if aircraft_type is not None else {})
            )
        ),
        "%h:%M",
    )


@register.simple_tag
def total_landings(reference_time: datetime, entries_filter: FilterSet | None = None) -> str:
    return str(
        statistics_total_landings(
            get_filtered_entries(entries_filter).filter(arrival_time__lte=reference_time),
            full_stop=False,
        )
    )
