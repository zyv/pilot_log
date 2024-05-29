from textwrap import wrap

from django.utils.safestring import mark_safe

from ..models.aircraft import Aircraft, FuelType
from .utils import AuthenticatedListView


def get_fuel_color_filter(name: str, color: str) -> str:
    r, g, b = (float(int(component, 16)) / 255 / 3 for component in wrap(color[1:], 2))
    return f"""
<filter id="fuel-{name}">
    <feColorMatrix type="matrix" values="
      {r} {r} {r} 0 0
      {g} {g} {g} 0 0
      {b} {b} {b} 0 0
      0 0 0 1 0" />
</filter>
    """


def get_fuel_color_filters() -> str:
    return mark_safe(
        f"""<svg id='fuel-color-filters'>{
            ''.join(get_fuel_color_filter(fuel.pk, fuel.color) for fuel in FuelType.objects.all())
        }</svg>""",
    )


class AircraftIndexView(AuthenticatedListView):
    model = Aircraft

    def get_context_data(self, *, object_list=None, **kwargs):
        return super().get_context_data(**kwargs) | {
            "aircraft_fields": {field.name: field for field in Aircraft._meta.get_fields()},
            "fuel_types": FuelType.objects.all(),
            "fuel_color_filters": get_fuel_color_filters(),
        }
