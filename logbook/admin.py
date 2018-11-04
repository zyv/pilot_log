from django.contrib import admin

from .models import Aerodrome, Aircraft, Certificate, LogEntry, Pilot

admin.site.register(Aerodrome)
admin.site.register(Aircraft)
admin.site.register(Certificate)
admin.site.register(LogEntry)
admin.site.register(Pilot)
