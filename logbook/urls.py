from django.urls import path

from .apps import LogbookConfig
from .views.certificates import CertificateIndexView
from .views.entries import EntryIndexView
from .views.experience import ExperienceIndexView
from .views.index import DashboardView

app_name = LogbookConfig.name


urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("entries/", EntryIndexView.as_view(), name="entries"),
    path("certificates/", CertificateIndexView.as_view(), name="certificates"),
    path("experience/", ExperienceIndexView.as_view(), name="experience"),
]
