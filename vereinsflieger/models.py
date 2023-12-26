import html
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from playwright.async_api import Page

from logbook.models.log_entry import FunctionType


@dataclass(frozen=True, kw_only=True)
class Person:
    first_name: str
    last_name: str


@dataclass(frozen=True, kw_only=True)
class Flight:
    registration: str
    from_aerodrome: str
    to_aerodrome: str
    departure_time: datetime
    arrival_time: datetime
    landings: int
    pilot: Person
    copilot: Optional[Person] = None
    function: FunctionType
    remarks: str = ""

    @classmethod
    def parse_pilot(cls, name: str) -> Person:
        pilot_last_name, pilot_first_name = map(str.strip, name.split(","))
        return Person(
            first_name=pilot_first_name,
            last_name=pilot_last_name,
        )

    @classmethod
    def parse_location(cls, location: str) -> str:
        return location.rsplit(" ", 1)[1]

    @classmethod
    def parse_datetime(cls, date: str, time: str) -> datetime:
        return datetime.fromisoformat(f"{date}T{time}+00:00")

    @classmethod
    def from_vereinsflieger_api(cls, data: dict) -> "Flight":
        if data["ft_education"] == "1":
            if data["uidattendant"] != "0":
                time_function = FunctionType.DUAL
                pilot = cls.parse_pilot(data["attendantname"])
                copilot = cls.parse_pilot(data["pilotname"])
            else:
                time_function = FunctionType.PIC
                pilot = cls.parse_pilot(data["pilotname"])
                copilot = cls.parse_pilot(data["finame"])
        else:
            time_function = FunctionType.PIC
            pilot = cls.parse_pilot(data["pilotname"])
            copilot = None

        return cls(
            registration=data["callsign"],
            from_aerodrome=cls.parse_location(data["departurelocation"]),
            to_aerodrome=cls.parse_location(data["arrivallocation"]),
            departure_time=cls.parse_datetime(data["dateofflight"], data["offblock"]),
            arrival_time=cls.parse_datetime(data["dateofflight"], data["onblock"]),
            landings=int(data["landingcount"]),
            pilot=pilot,
            copilot=copilot,
            function=time_function,
            remarks=html.unescape(data["comment"]),
        )

    @classmethod
    async def from_vereinsflieger_scraper(cls, page: Page) -> "Flight":
        registration = await page.locator(":text('CallSign') + td").text_content()

        from_aerodrome = cls.parse_location(await page.locator(":text('Startort') + td").text_content())
        to_aerodrome = cls.parse_location(await page.locator(":text('Landeort') + td").text_content())

        flight_date = "-".join(reversed((await page.locator(":text('Datum') + td").text_content()).split(".")))
        departure_time = cls.parse_datetime(flight_date, await page.locator(":text('Off-Block') + td").text_content())
        arrival_time = cls.parse_datetime(flight_date, await page.locator(":text('On-Block') + td").text_content())

        landings = int(await page.locator(":text('Landungen') + td").text_content())

        flight_type = await page.locator(":text('Flugart') + td").text_content()

        if flight_type.startswith("S"):
            if (await page.query_selector(":text('Flugauftrag von') + td")) is not None:
                time_function = FunctionType.PIC
                pilot = cls.parse_pilot(await page.locator(":text('Pilot') + td").text_content())
                copilot = cls.parse_pilot(await page.locator(":text('Flugauftrag von') + td").text_content())
            elif (await page.query_selector(":text('Begleiter / FI') + td")) is not None:
                time_function = FunctionType.DUAL
                pilot = cls.parse_pilot(await page.locator(":text('Begleiter / FI') + td").text_content())
                copilot = cls.parse_pilot(await page.locator(":text('Pilot') + td").text_content())
            else:
                raise NotImplementedError
        elif flight_type.startswith("N"):
            time_function = FunctionType.PIC
            pilot = cls.parse_pilot(await page.locator(":text('Pilot') + td").text_content())
            copilot = None
        else:
            raise NotImplementedError

        remarks = await page.locator(":text('Kommentar') + td").text_content()

        return cls(
            registration=registration,
            from_aerodrome=from_aerodrome,
            to_aerodrome=to_aerodrome,
            departure_time=departure_time,
            arrival_time=arrival_time,
            landings=landings,
            pilot=pilot,
            copilot=copilot,
            function=time_function,
            remarks=remarks,
        )
