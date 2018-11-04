from django.contrib import admin

from .models import Aerodrome, Aircraft, Certificate, LogEntry, Pilot


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
    save_as = True


@admin.register(Pilot)
class PilotAdmin(admin.ModelAdmin):
    search_fields = ("first_name", "last_name")


admin.site.register(Certificate)
