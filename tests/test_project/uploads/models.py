from django.db import models


class Document(models.Model):
    """A minimal model with a ``FileField`` for upload-path tests (#241)."""

    title = models.CharField(max_length=100)
    attachment = models.FileField(upload_to="docs/", blank=True)

    def __str__(self) -> str:
        return self.title
