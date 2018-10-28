from django.urls import path

from logbook import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
