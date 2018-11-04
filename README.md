# Pilot Log

This is a simple general aviation private pilot logbook web application, geared towards those of us frequently flying multiple types of light aircraft.

It is being developed to provide a personal migration path from the excellent [FlightLog](http://warbredstudios.com/flightlog/flightlog.html) for Android software by Jeff Cardillo and released in the hope that it will be useful to other private pilots.

## Requirements

* Python 3.6+
* Django 2.1

## Usage

```
./manage.py dumpdata logbook --exclude logbook.Aerodrome --exclude logbook.LogEntry > logbook/fixtures/logbook.json
```

## License

This project is released under the terms of the MIT license. Full details in the `LICENSE` file.
