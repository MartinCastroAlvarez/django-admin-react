"""Django AppConfig for django_admin_react.

Registering this AppConfig in the consumer's `INSTALLED_APPS` is the
only side effect of adding the package. The real wiring (URLs, API,
templates, static assets) is opt-in via the consumer's own `urls.py`.
"""

from django.apps import AppConfig
from django.core.checks import register


class DjangoAdminReactConfig(AppConfig):
    """Django app config — the only side effect of adding the package.

    The four attributes are the standard Django ``AppConfig`` contract:

    - ``name`` — Python import path; required by Django's app registry.
    - ``label`` — short identifier used in migrations and admin URLs.
    - ``verbose_name`` — human-readable name shown in the admin index.
    - ``default_auto_field`` — bigint primary keys for any future models
      the package adds (none today, but pinning the default avoids a
      Django warning and locks the choice in for forwards compat).
    """

    name = "django_admin_react"
    label = "django_admin_react"
    verbose_name = "Django Admin React"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Register the package's system checks at app-load (#667).

        Importing + registering here (not at module import time) keeps the
        checks tied to the app registry being ready, matching Django's
        documented pattern. The import is local so adding the app has no
        eager import cost beyond the AppConfig itself.
        """
        from django_admin_react.checks import check_django_admin_react

        register(check_django_admin_react)
