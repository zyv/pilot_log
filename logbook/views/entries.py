from itertools import chain

from django import forms
from django.conf import settings
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView

from vereinsflieger.vereinsflieger import import_from_vereinsflieger

from ..models.aerodrome import Aerodrome
from ..models.aircraft import Aircraft
from ..models.log_entry import LogEntry
from ..models.pilot import Pilot
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

        pilot, _ = Pilot.objects.get_or_create(first_name=flight.pilot.first_name, last_name=flight.pilot.last_name)

        copilot, _ = (
            Pilot.objects.get_or_create(first_name=flight.copilot.first_name, last_name=flight.copilot.last_name)
            if flight.copilot is not None
            else (None, None)
        )

        return flight_id, LogEntry.objects.create(
            aircraft=aircraft,
            from_aerodrome=from_aerodrome,
            to_aerodrome=to_aerodrome,
            departure_time=departure_time,
            arrival_time=arrival_time,
            landings=flight.landings,
            time_function=flight.function,
            pilot=pilot,
            copilot=copilot,
            remarks=flight.remarks,
            cross_country="XC" in flight.remarks or "Nav." in flight.remarks,
        )


class EntryIndexView(AuthenticatedListView, FormView):
    model = LogEntry
    ordering = "arrival_time"
    paginate_by = 7

    form_class = VereinsfliegerForm
    success_url = reverse_lazy("logbook:entries")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        # Due to slots, `object_list|last` in the template can possibly be None, so provide the last "real" entry
        context["last_entry"] = (
            [entry for entry in context["object_list"] if entry is not None][-1]
            if len(context["object_list"])
            else None
        )

        return context | {"form": self.get_form()}

    def paginate_queryset(self, queryset, page_size):
        # Take slots into account
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
