from ..models import Aircraft
from .utils import AuthenticatedListView


class AircraftIndexView(AuthenticatedListView):
    model = Aircraft

    def get_context_data(self, *, object_list=None, **kwargs):
        return super().get_context_data(**kwargs) | {
            "aircraft_fields": {field.name: field for field in Aircraft._meta.get_fields()},
        }
