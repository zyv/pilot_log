from itertools import chain

from django import forms
from django.conf import settings
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView

from vereinsflieger.vereinsflieger import import_from_vereinsflieger

from ..models import Aerodrome, Aircraft, LogEntry, Pilot
from .utils import AuthenticatedListView


class VereinsfliegerForm(forms.Form):
    flight_id = forms.IntegerField(
        label="Vereinsflieger Flight ID",
        help_text="The ID of the flight to import from Vereinsflieger (Allgemeine Daten / Eintrag)",
        widget=forms.TextInput(
            attrs={
                "min": 1,
                "placeholder": "123456",
            },
        ),
    )

    def import_flight(self) -> (int, LogEntry):
        flight_id = self.cleaned_data["flight_id"]
        flight = import_from_vereinsflieger(settings, flight_id)

        aircraft = Aircraft.objects.get(registration=flight.registration)

        departure_time = flight.departure_time
        arrival_time = flight.arrival_time

        from_aerodrome = Aerodrome.objects.get(icao_code=flight.from_aerodrome)
        to_aerodrome = Aerodrome.objects.get(icao_code=flight.to_aerodrome)

        return flight_id, LogEntry.objects.create(
            aircraft=aircraft,
            from_aerodrome=from_aerodrome,
            to_aerodrome=to_aerodrome,
            departure_time=departure_time,
            arrival_time=arrival_time,
            landings=flight.landings,
            time_function=flight.function,
            pilot=Pilot.objects.get(first_name=flight.pilot.first_name, last_name=flight.pilot.last_name),
            copilot=(
                Pilot.objects.get(first_name=flight.copilot.first_name, last_name=flight.copilot.last_name)
                if flight.copilot is not None
                else None
            ),
            remarks=flight.remarks,
            cross_country="XC" in flight.remarks,
        )


class EntryIndexView(AuthenticatedListView, FormView):
    model = LogEntry
    ordering = "arrival_time"
    paginate_by = 7

    form_class = VereinsfliegerForm
    success_url = reverse_lazy("logbook:entries")

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(*args, **kwargs) | {"form": self.get_form()}

    def paginate_queryset(self, queryset, page_size):
        entries = tuple(chain.from_iterable(([entry] + [None] * (entry.slots - 1)) for entry in queryset))

        # Set last page as a default to mimic paper logbook
        if not self.request.GET.get(self.page_kwarg):
            self.kwargs[self.page_kwarg] = "last"

        return super().paginate_queryset(entries, page_size)

    def form_valid(self, form):
        flight_id, log_entry = form.import_flight()
        messages.success(self.request, f"Flight #{flight_id} imported successfully as #{log_entry.id}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().get(self.request, *self.args, **self.kwargs)
