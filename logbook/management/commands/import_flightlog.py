import csv
import enum
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand

import logbook.models.aerodrome
import logbook.models.aircraft
import logbook.models.log_entry
import logbook.models.pilot


class Fields(enum.StrEnum):
    DATE = "Date"
    REGISTRATION = "Registration"
    FROM = "From"
    TO = "To"
    TOTAL_TIME = "Total Time"
    TIME_PIC = "PIC"
    TIME_DUAL = "Dual"
    LANDINGS = "Landings"
    COPILOT = "0. Co-pilot"
    DEPARTURE_TIME = "1. Start time"
    ARRIVAL_TIME = "2. Landing time"
    NOTE = "Note"


class Command(BaseCommand):
    help = "Imports data from FlightLog CSV reports"

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)

        parser.add_argument(
            "--init",
            action="store_true",
            dest="init",
            default=False,
            help="Re-initialize the database by removing all entries and importing them anew",
        )

    def handle(self, *args, **options):
        if options["init"]:
            self.stdout.write(self.style.WARNING("Removing old database records..."))
            logbook.models.log_entry.LogEntry.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Importing FlightLog records..."))

        with Path(options["filename"]).open(newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                day, month, year = [int(value) for value in row[Fields.DATE].split("/")]
                hour_departure, minute_departure = [int(value) for value in row[Fields.DEPARTURE_TIME].split(":")]
                hour_arrival, minute_arrival = [int(value) for value in row[Fields.ARRIVAL_TIME].split(":")]

                departure_time = datetime(year, month, day, hour_departure, minute_departure, tzinfo=UTC)
                arrival_time = datetime(year, month, day, hour_arrival, minute_arrival, tzinfo=UTC)

                duration_recorded = (hour_arrival * 60 + minute_arrival) - (hour_departure * 60 + minute_departure)
                duration_computed = (arrival_time - departure_time).total_seconds() / 60

                assert duration_computed == duration_recorded, f"{duration_computed}, {duration_recorded}"

                pic_time, _ = map(int, row[Fields.TIME_PIC].split(":"))
                dual_time, _ = map(int, row[Fields.TIME_DUAL].split(":"))

                assert (pic_time + dual_time) == duration_recorded, f"{duration_recorded}, {pic_time}, {dual_time}"
                assert bool(pic_time) ^ bool(dual_time)

                time_function = (
                    logbook.models.log_entry.FunctionType.PIC
                    if pic_time
                    else logbook.models.log_entry.FunctionType.DUAL
                )
                registration = row[Fields.REGISTRATION]

                aircraft = logbook.models.aircraft.Aircraft.objects.get(registration=registration)

                me = logbook.models.pilot.Pilot.objects.get(last_name="Zaytsev")
                recorded_copilot = logbook.models.pilot.Pilot.objects.get(last_name=row[Fields.COPILOT].strip())

                pilot, copilot = (
                    (me, recorded_copilot)
                    if time_function is logbook.models.log_entry.FunctionType.PIC
                    else (recorded_copilot, me)
                )

                from_aerodrome = logbook.models.aerodrome.Aerodrome.objects.get(icao_code=row[Fields.FROM].strip())
                to_aerodrome = logbook.models.aerodrome.Aerodrome.objects.get(icao_code=row[Fields.TO].strip())

                remarks = row[Fields.NOTE].strip()

                launch_type = (
                    {
                        "Self": logbook.models.log_entry.LaunchType.SELF,
                        "Tow": logbook.models.log_entry.LaunchType.TOW,
                        "Winch": logbook.models.log_entry.LaunchType.WINCH,
                    }[remarks]
                    if aircraft.type == logbook.models.aircraft.AircraftType.GLD
                    else ""
                )

                # Clear remarks field, if used for glider launch type
                if launch_type:
                    remarks = ""

                self.stdout.write(
                    "Processing entry "
                    f"{departure_time.date()} {departure_time.time()} {arrival_time.time()} {aircraft.registration} "
                    f"{from_aerodrome.icao_code} -> {to_aerodrome.icao_code} {pilot.last_name} / {copilot.last_name} "
                    f"{f'({remarks})' if remarks else ''}",
                )

                defaults = {
                    "aircraft": aircraft,
                    "from_aerodrome": from_aerodrome,
                    "to_aerodrome": to_aerodrome,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "landings": int(row[Fields.LANDINGS]),
                    "time_function": time_function,
                    "pilot": pilot,
                    "copilot": copilot,
                    "launch_type": launch_type,
                    "remarks": remarks,
                }

                entry, created = logbook.models.log_entry.LogEntry.objects.update_or_create(
                    departure_time=departure_time,
                    from_aerodrome=from_aerodrome,
                    defaults=defaults,
                )

                self.stdout.write(("Created new object" if created else "Updated object") + f" (pk={entry.id})")

        self.stdout.write(self.style.SUCCESS("Successfully completed FlightLog import!"))
