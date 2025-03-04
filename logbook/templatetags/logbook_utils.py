import datetime
from string import Template

from django import template
from django.template import TemplateSyntaxError
from django.utils.safestring import mark_safe

from ..models.aircraft import SpeedUnit
from ..statistics.experience import ExperienceRecord, TotalsRecord

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
