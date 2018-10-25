import csv
from datetime import datetime, timezone

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from logbook import models

FIELD_DATE = "Date"
FIELD_REGISTRATION = "Registration"
FIELD_FROM = "From"
FIELD_TO = "To"
FIELD_TOTAL_TIME = "Total Time"
FIELD_TIME_PIC = "PIC"
FIELD_TIME_DUAL = "Dual"
FIELD_LANDINGS = "Landings"
FIELD_COPILOT = "0. Co-pilot"
FIELD_DEPARTURE_TIME = "1. Start time"
FIELD_ARRIVAL_TIME = "2. Landing time"


class Command(BaseCommand):
    help = "Imports data from FlightLog CSV reports"

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="?", type=str)

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Importing FlightLog records..."))

        with open(options["filename"], newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                day, month, year = [int(value) for value in row[FIELD_DATE].split("/")]
                hour_departure, minute_departure = [int(value) for value in row[FIELD_DEPARTURE_TIME].split(":")]
                hour_arrival, minute_arrival = [int(value) for value in row[FIELD_ARRIVAL_TIME].split(":")]

                departure_time = datetime(year, month, day, hour_departure, minute_departure, tzinfo=timezone.utc)
                arrival_time = datetime(year, month, day, hour_arrival, minute_arrival, tzinfo=timezone.utc)

                duration_recorded = (hour_arrival * 60 + minute_arrival) - (hour_departure * 60 + minute_departure)
                duration_computed = (arrival_time - departure_time).total_seconds() / 60

                assert duration_computed == duration_recorded, f"{duration_computed}, {duration_recorded}"

                pic_time, _ = map(int, row[FIELD_TIME_PIC].split(":"))
                dual_time, _ = map(int, row[FIELD_TIME_DUAL].split(":"))

                assert (pic_time + dual_time) == duration_recorded, f"{duration_recorded}, {pic_time}, {dual_time}"
                assert bool(pic_time) ^ bool(dual_time)

                time_function = models.FunctionType.PIC if pic_time else models.FunctionType.DUAL
                registration = row[FIELD_REGISTRATION]

                aircraft = models.Aircraft.objects.get(registration=registration)

                me = models.Pilot.objects.get(last_name="Zaytsev")
                recorded_copilot = models.Pilot.objects.get(last_name=row[FIELD_COPILOT].strip())

                pilot, copilot = \
                    (me, recorded_copilot) if time_function is models.FunctionType.PIC else (recorded_copilot, me)

                from_aerodrome = row[FIELD_FROM].strip()
                to_aerodrome = row[FIELD_TO].strip()

                self.stdout.write(
                    f"{departure_time.date()} {departure_time.time()} {arrival_time.time()} {aircraft.registration} "
                    f"{from_aerodrome} -> {to_aerodrome} {pilot.last_name} / {copilot.last_name}"
                )

                # TODO: add support for launch type detection

                try:
                    entry = models.LogEntry.objects.get(departure_time=departure_time)
                except ObjectDoesNotExist:
                    models.LogEntry.objects.create(
                        aircraft=aircraft,
                        from_aerodrome=from_aerodrome,
                        to_aerodrome=to_aerodrome,
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                        landings=int(row[FIELD_LANDINGS]),
                        time_function=time_function.name,
                        pilot=pilot,
                        copilot=copilot,
                    )
                else:
                    self.stdout.write(f"Entry already exists (pk={entry.id})!")
                    # TODO: update?

        self.stdout.write(self.style.SUCCESS("Successfully completed FlightLog import!"))
