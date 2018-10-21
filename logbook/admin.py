from django.contrib import admin

from .models import Aircraft, LogEntry

admin.site.register(Aircraft)
admin.site.register(LogEntry)
