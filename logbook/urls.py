from django.urls import path

from logbook import views

urlpatterns = [
    path("", views.index, name="index"),
]
