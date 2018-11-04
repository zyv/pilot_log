from django.contrib import admin

from .models import Aerodrome, Aircraft, Certificate, LogEntry, Pilot


@admin.register(Aerodrome)
class AerodromeAdmin(admin.ModelAdmin):
    search_fields = ("name", "icao_code")


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    autocomplete_fields = ("from_aerodrome", "to_aerodrome")
    radio_fields = {
        "time_function": admin.VERTICAL,
        "launch_type": admin.VERTICAL,
    }
    save_as = True


admin.site.register(Aircraft)
admin.site.register(Certificate)
admin.site.register(Pilot)
