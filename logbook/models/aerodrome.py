from django.db import models
from django_countries.fields import CountryField


class Aerodrome(models.Model):
    name = models.CharField(max_length=75)
    city = models.CharField(max_length=75)
    country = CountryField()
    icao_code = models.CharField(max_length=4, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    elevation = models.IntegerField()
    priority = models.IntegerField()

    class Meta:
        ordering = ("priority",)

    def __str__(self):
        return f"{self.icao_code} ({self.name})"
