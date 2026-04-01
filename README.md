# Pilot Log

This is a simple general aviation private pilot logbook web application, geared towards those of us frequently flying multiple types of light aircraft. Log entries management is to be performed via the Django admin interface. Custom views can be used for statistics and to obtain a print representation.

It is being developed to provide a personal migration path from the excellent [FlightLog](http://warbredstudios.com/flightlog/flightlog.html) for Android software by Jeff Cardillo and released in the hope that it will be useful to other private pilots.

## Requirements

* Python 3.12+
* Django LTS

## Usage

```
poetry install

./manage.py migrate
./manage.py createsuperuser
./manage.py shell < logbook/fixtures/import_aerodromes.py
./manage.py loaddata logbook/fixtures/fuel_type.json
./manage.py runserver
```

## License

This project is released under the terms of the MIT license. Full details in the `LICENSE` file.

## Upgrading to Django 6.x

### Template Partials

> The Django Template Language now supports template partials, making it easier to encapsulate and reuse small named fragments within a template file. The new tags {% partialdef %} and {% partial %} define a partial and render it, respectively.
>
> Partials can also be referenced using the template_name#partial_name syntax with get_template(), render(), {% include %}, and other template-loading tools, enabling more modular and maintainable templates without needing to split components into separate files.

### How to use Django’s Content Security Policy

https://docs.djangoproject.com/en/6.0/howto/csp/
