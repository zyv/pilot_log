from itertools import chain

import django_filters
from django import forms
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import FormView
from django_filters.views import FilterView

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


class LogEntriesFilter(django_filters.FilterSet):
    @staticmethod
    def filter_by_aerodrome(queryset, _, value):
        return queryset.filter(Q(from_aerodrome=value) | Q(to_aerodrome=value))

    registration = django_filters.AllValuesFilter(field_name="aircraft__registration")
    aerodrome = django_filters.ModelChoiceFilter(
        label="Aerodrome", method="filter_by_aerodrome", queryset=Aerodrome.objects.all()
    )

    class Meta:
        model = LogEntry
        fields = ("registration", "aerodrome")


class EntryIndexView(FilterView, AuthenticatedListView, FormView):
    model = LogEntry
    ordering = "arrival_time"

    form_class = VereinsfliegerForm
    success_url = reverse_lazy("logbook:entries")

    filterset_class = LogEntriesFilter
    template_name_suffix = "_list"

    def filtering_is_active(self):
        return self.filterset.form.is_valid() and any(self.filterset.form.cleaned_data.values())

    def get_paginate_by(self, queryset):
        # Disable pagination if filtering is active
        return None if self.filtering_is_active() else 7

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
        # Create empty entries for slots, but only if filtering is NOT active
        entries = tuple(
            chain.from_iterable(
                [entry] + ([None] * (entry.slots - 1) if not self.filtering_is_active() else []) for entry in queryset
            )
        )

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
