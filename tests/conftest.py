from datetime import UTC, datetime, timedelta

import pytest

from logbook.models.aerodrome import Aerodrome
from logbook.models.aircraft import Aircraft, AircraftType
from logbook.models.log_entry import LogEntry, LogEntryQuerySet
from logbook.models.pilot import Pilot

NUMBER_OF_LOG_ENTRIES = 30
EXTRA_LANDINGS = 2


@pytest.fixture
def log_entries() -> LogEntryQuerySet[LogEntry]:
    aircraft = Aircraft.objects.create(
        type=AircraftType.SEP,
        maker="Test",
        model="Test",
        icao_designator="TEST",
        registration="TEST",
    )
    aerodrome = Aerodrome.objects.create(
        name="Test",
        city="Test",
        country="DE",
        icao_code="TEST",
        latitude=0,
        longitude=0,
        elevation=0,
        priority=0,
    )
    pilot = Pilot.objects.create(first_name="Test", last_name="Test")

    for i in range(NUMBER_OF_LOG_ENTRIES):
        LogEntry.objects.create(
            aircraft=aircraft,
            from_aerodrome=aerodrome,
            to_aerodrome=aerodrome,
            departure_time=datetime.now(tz=UTC) - timedelta(days=110 - i),
            arrival_time=datetime.now(tz=UTC) - timedelta(days=110 - i) + timedelta(minutes=1),
            landings=1,
            pilot=pilot,
        )

    first_entry = LogEntry.objects.get(pk=1)
    first_entry.landings = EXTRA_LANDINGS + 1
    first_entry.save()

    return LogEntry.objects.all()
