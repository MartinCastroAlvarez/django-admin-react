from django.db import models


class Pipeline(models.Model):
    """A ``Job``-style model whose admin declares a deliberately large set of
    actions (12 batch + 2 detail-only) so the detail-page toolbar is forced to
    wrap onto multiple lines — the regression fixture for #672.

    A single row of 14 buttons (several with long descriptions) is visibly
    impossible at any reasonable viewport, so the SPA's stacked-header +
    ``flex-wrap`` toolbar layout has to reflow them rather than push the title
    or breadcrumb off-screen.
    """

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=32, default="idle")

    def __str__(self) -> str:
        return self.name
