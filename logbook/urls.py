from django.urls import path

from logbook import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
]
