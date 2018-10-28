from django.urls import path

from logbook import views
from .apps import LogbookConfig

app_name = LogbookConfig.name

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("entries/", views.EntryIndexView.as_view(), name="entries"),
]
