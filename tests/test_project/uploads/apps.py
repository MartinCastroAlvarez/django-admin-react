from django.apps import AppConfig


class UploadsConfig(AppConfig):
    """Test-only app providing a model with a ``FileField`` so the upload
    write path (#241) has something to exercise — the rest of the test
    project rides on Django's built-in models, none of which have files."""

    default_auto_field = "django.db.models.AutoField"
    name = "tests.test_project.uploads"
    label = "uploads"
