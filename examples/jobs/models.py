from django.db import models


class Job(models.Model):
    """A background job whose admin mixes a stock change form with a custom,
    request-driven step-sequencing view — see ``admin.JobAdmin``."""

    name = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, default="idle")

    def __str__(self) -> str:
        return self.name
