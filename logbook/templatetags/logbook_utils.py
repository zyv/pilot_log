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

    substitutions = {
        "H": f"{hours:02.0f}",
        "h": f"{hours:.0f}",
        "M": f"{minutes:02.0f}",
        "m": f"{minutes:.0f}",
        "S": f"{seconds:02.0f}",
        "s": f"{seconds:.0f}",
    }

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
