# Pilot Log

This is a simple general aviation private pilot logbook web application, geared towards those of us frequently flying multiple types of light aircraft. Log entries management is to be performed via Django admin interface. Custom views can be used for statistics and to obtain a print representation.

It is being developed to provide a personal migration path from the excellent [FlightLog](http://warbredstudios.com/flightlog/flightlog.html) for Android software by Jeff Cardillo and released in the hope that it will be useful to other private pilots.

## Requirements

* Python 3.11+
* Django

## Usage

```
poetry install

./manage.py migrate
./manage.py createsuperuser
./manage.py loaddata logbook/fixtures/data/aerodromes.json
./manage.py runserver
```

## License

This project is released under the terms of the MIT license. Full details in the `LICENSE` file.
