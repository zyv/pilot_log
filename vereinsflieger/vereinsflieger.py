from asgiref.sync import async_to_sync
from django.conf import LazySettings

from .models import Flight
from .vereinsflieger_api import VereinsfliegerApiSession
from .vereinsflieger_scraper import VereinsfliegerScraperSession


def import_from_vereinsflieger_api(settings: LazySettings, flight_id: int) -> Flight:
    with VereinsfliegerApiSession(
        app_key=settings.VEREINSFLIEGER_APP_KEY,
        username=settings.VEREINSFLIEGER_USERNAME,
        password=settings.VEREINSFLIEGER_PASSWORD,
    ) as vs:
        return vs.get_flight(flight_id)


@async_to_sync
async def import_from_vereinsflieger_scraper(settings: LazySettings, flight_id: int) -> Flight:
    async with VereinsfliegerScraperSession(
        username=settings.VEREINSFLIEGER_USERNAME,
        password=settings.VEREINSFLIEGER_PASSWORD,
        debug=settings.DEBUG,
    ) as vs:
        return await vs.get_flight(flight_id)


def import_from_vereinsflieger(settings: LazySettings, flight_id: int) -> Flight:
    return (
        import_from_vereinsflieger_scraper(settings, flight_id)
        if settings.VEREINSFLIEGER_APP_KEY is None
        else import_from_vereinsflieger_api(settings, flight_id)
    )
