from django.contrib import admin

from .models import Aerodrome, Aircraft, Certificate, LogEntry, Pilot


class LogEntryAdmin(admin.ModelAdmin):
    save_as = True


admin.site.register(Aerodrome)
admin.site.register(Aircraft)
admin.site.register(Certificate)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Pilot)
