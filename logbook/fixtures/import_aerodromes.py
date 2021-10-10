import csv
import json
import logging
from decimal import Decimal

from django_countries import countries

from logbook.models import Aerodrome

CHECK_ICAO_CODE = False

logging.basicConfig(level=logging.DEBUG)


# Reference data from http://ourairports.com/data/
def load_reference_icao_codes():
    icao_codes = set()

    with open("logbook/fixtures/data/airports.csv", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            icao_codes.add(row["ident"])

    return icao_codes


def load_bitbringers_data():
    with open("logbook/fixtures/data/aerodromes.json", "r") as fp:
        return json.load(fp, parse_float=Decimal)


if CHECK_ICAO_CODE:
    reference_codes = load_reference_icao_codes()

suspicious_codes = set()

for aerodrome in load_bitbringers_data():

    aerodrome_icao_code = aerodrome["icao"]

    if CHECK_ICAO_CODE and aerodrome_icao_code not in reference_codes:
        suspicious_codes.add(aerodrome_icao_code)

    aerodrome_name = aerodrome["name"]
    aerodrome_city = aerodrome["city"]
    aerodrome_country = countries.by_name(aerodrome["country"])

    if not any([aerodrome_name, aerodrome_city, aerodrome_country]):
        logging.warning(f"Empty name/city/country for {aerodrome_icao_code}!")

    obj, created = Aerodrome.objects.update_or_create(
        icao_code=aerodrome_icao_code,
        defaults={
            "name": aerodrome_name,
            "city": aerodrome_city,
            "country": aerodrome_country,
            "latitude": aerodrome["lat"],
            "longitude": aerodrome["lng"],
            "elevation": aerodrome["elev"],
            "priority": aerodrome["distance"],
        },
    )

    logging.debug(f"{'Created' if created else 'Updated'} aerodrome: {obj}")

if suspicious_codes:
    logging.warning(f"Found suspicious codes: {len(suspicious_codes)}")
    logging.warning(suspicious_codes)
