import datetime
from string import Template

from django import template

from ..views.utils import ExperienceRecord, TotalsRecord

register = template.Library()


class DurationTemplate(Template):
    delimiter = "%"


@register.filter
def duration(value: datetime.timedelta, format_specification: str = "%H:%M:%S"):
    hours, remainder = divmod(value.total_seconds(), 60 * 60)
    minutes, seconds = divmod(remainder, 60)

    def pad(number: float) -> str:
        return f"{number:02.0f}"

    def ceil(number: float) -> str:
        return f"{number:.0f}"

    ds = {"d": value.days, "h": hours, "m": minutes, "s": seconds}
    substitutions = {k.upper(): pad(v) for k, v in ds.items()} | {k.lower(): ceil(v) for k, v in ds.items()}

    return DurationTemplate(format_specification).substitute(**substitutions)


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
