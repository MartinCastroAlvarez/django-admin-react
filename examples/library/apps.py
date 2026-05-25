from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "examples.library"
    label = "library"
    verbose_name = "Library"
