from django.contrib import admin

from .models import Aerodrome, Aircraft, Certificate, LogEntry, Pilot
from .templatetags.logbook_utils import duration


@admin.register(Aerodrome)
class AerodromeAdmin(admin.ModelAdmin):
    search_fields = ("name", "icao_code")


@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    search_fields = ("registration",)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    autocomplete_fields = ("aircraft", "from_aerodrome", "to_aerodrome", "pilot", "copilot")
    radio_fields = {
        "time_function": admin.VERTICAL,
        "launch_type": admin.VERTICAL,
    }
    list_display = ("get_time", "get_registration", "get_from", "get_to", "pilot", "copilot")
    list_filter = ("time_function",)
    save_as = True

    def get_time(self, obj):
        return (obj.departure_time.strftime("%Y-%m-%d %H:%M") +
                f" {duration(obj.arrival_time - obj.departure_time, '(%H:%M)')}")

    get_time.short_description = "Time"
    get_time.admin_order_field = "departure_time"

    def get_registration(self, obj):
        return obj.aircraft.registration

    get_registration.short_description = "Tail No."
    get_registration.admin_order_field = "aircraft__registration"

    def get_from(self, obj):
        return obj.from_aerodrome.icao_code

    get_from.short_description = "From"
    get_from.admin_order_field = "from_aerodrome__icao_code"

    def get_to(self, obj):
        return obj.to_aerodrome.icao_code

    get_to.short_description = "To"
    get_to.admin_order_field = "to_aerodrome__icao_code"


@admin.register(Pilot)
class PilotAdmin(admin.ModelAdmin):
    search_fields = ("first_name", "last_name")


admin.site.register(Certificate)
