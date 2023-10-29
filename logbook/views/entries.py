import html
from datetime import datetime
from itertools import chain

from django import forms
from django.conf import settings
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView

from vereinsflieger.vereinsflieger import VereinsfliegerSession

from ..models import Aerodrome, Aircraft, AircraftType, FunctionType, LogEntry, Pilot
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

        with VereinsfliegerSession(
            app_key=settings.VEREINSFLIEGER_APP_KEY,
            username=settings.VEREINSFLIEGER_USERNAME,
            password=settings.VEREINSFLIEGER_PASSWORD,
        ) as vs:
            flight_data = vs.get_flight(flight_id)

        aircraft = Aircraft.objects.get(registration=flight_data["callsign"])

        departure_time = datetime.fromisoformat(f"{flight_data['dateofflight']}T{flight_data['offblock']}+00:00")
        arrival_time = datetime.fromisoformat(f"{flight_data['dateofflight']}T{flight_data['onblock']}+00:00")

        aerodrome_from = Aerodrome.objects.get(icao_code=flight_data["departurelocation"].rsplit(" ", 1)[1])
        aerodrome_to = Aerodrome.objects.get(icao_code=flight_data["arrivallocation"].rsplit(" ", 1)[1])

        def parse_pilot(name: str) -> Pilot:
            pilot_last_name, pilot_first_name = map(str.strip, name.split(","))
            return Pilot.objects.get(first_name=pilot_first_name, last_name=pilot_last_name)

        if flight_data["ft_education"] == "1":
            if flight_data["uidattendant"] != "0":
                time_function = FunctionType.DUAL
                pilot = parse_pilot(flight_data["attendantname"])
                copilot = parse_pilot(flight_data["pilotname"])
            else:
                time_function = FunctionType.PIC
                pilot = parse_pilot(flight_data["pilotname"])
                copilot = parse_pilot(flight_data["finame"])
        else:
            time_function = FunctionType.PIC
            pilot = parse_pilot(flight_data["pilotname"])
            copilot = None

        return flight_id, LogEntry.objects.create(
            aircraft=aircraft,
            from_aerodrome=aerodrome_from,
            to_aerodrome=aerodrome_to,
            departure_time=departure_time,
            arrival_time=arrival_time,
            landings=int(flight_data["landingcount"]),
            time_function=time_function.name,
            pilot=pilot,
            copilot=copilot,
            remarks=html.unescape(flight_data["comment"]),
            cross_country="XC" in flight_data["comment"],
        )


class EntryIndexView(AuthenticatedListView, FormView):
    model = LogEntry
    ordering = "arrival_time"
    paginate_by = 7

    form_class = VereinsfliegerForm
    success_url = reverse_lazy("logbook:entries")

    def post(self, request, *args, **kwargs):
        return super().get(self, request, *args, **kwargs)

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

    def form_valid(self, form):
        flight_id, log_entry = form.import_flight()
        messages.success(self.request, f"Flight #{flight_id} imported successfully as #{log_entry.id}!")
        return super().form_valid(form)
