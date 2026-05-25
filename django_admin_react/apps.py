"""Django AppConfig for django_admin_react.

Registering this AppConfig in the consumer's `INSTALLED_APPS` is the
only side effect of adding the package. The real wiring (URLs, API,
templates, static assets) is opt-in via the consumer's own `urls.py`.
"""

from django.apps import AppConfig


class DjangoAdminReactConfig(AppConfig):
    name = "django_admin_react"
    label = "django_admin_react"
    verbose_name = "Django Admin React"
    default_auto_field = "django.db.models.BigAutoField"
