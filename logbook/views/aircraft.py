from logbook.models import Aircraft
from logbook.views.utils import AuthenticatedListView, CurrencyStatus


class AircraftIndexView(AuthenticatedListView):
    model = Aircraft

    def get_context_data(self, *, object_list=None, **kwargs):
        return super().get_context_data(**kwargs) | {
            "CurrencyStatus": CurrencyStatus.__members__,
            "aircraft_fields": {field.name: field for field in Aircraft._meta.get_fields()},
        }
