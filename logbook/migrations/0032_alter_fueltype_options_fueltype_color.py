# Generated by Django 5.0.6 on 2024-05-29 15:18

import colorfield.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("logbook", "0031_fueltype_aircraft_fuel_types"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="fueltype",
            options={"ordering": ("-density",)},
        ),
        migrations.AddField(
            model_name="fueltype",
            name="color",
            field=colorfield.fields.ColorField(default="#00FFFF", image_field=None, max_length=25, samples=None),
        ),
    ]