from django.contrib import admin

from .models import Aerodrome, Aircraft, Certificate, LogEntry, Pilot


class AerodromeAdmin(admin.ModelAdmin):
    search_fields = ("name", "icao_code")


class LogEntryAdmin(admin.ModelAdmin):
    autocomplete_fields = ("from_aerodrome", "to_aerodrome")
    save_as = True


admin.site.register(Aerodrome, AerodromeAdmin)
admin.site.register(Aircraft)
admin.site.register(Certificate)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Pilot)
