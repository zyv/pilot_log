# Generated by Django 4.0 on 2022-01-05 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logbook", "0006_alter_aircraft_registration"),
    ]

    operations = [
        migrations.AddField(
            model_name="logentry",
            name="cross_country",
            field=models.BooleanField(default=False),
        ),
    ]