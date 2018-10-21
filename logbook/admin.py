from django.contrib import admin

from .models import Aircraft, Pilot, LogEntry

admin.site.register(Aircraft)
admin.site.register(Pilot)
admin.site.register(LogEntry)
