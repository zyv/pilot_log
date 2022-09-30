from itertools import chain

from ..models import AircraftType, FunctionType, LogEntry
from .utils import AuthenticatedListView


class EntryIndexView(AuthenticatedListView):
    model = LogEntry
    ordering = "arrival_time"
    paginate_by = 7

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(*args, **kwargs) | {
            "aircraft_types": list(AircraftType),
            "function_types": list(FunctionType),
        }

    def paginate_queryset(self, queryset, page_size):
        entries = tuple(chain.from_iterable(([entry] + [None] * (entry.slots - 1)) for entry in queryset))

        # Set last page as a default to mimic paper logbook
        if not self.request.GET.get(self.page_kwarg):
            self.kwargs[self.page_kwarg] = "last"

        return super().paginate_queryset(entries, page_size)
