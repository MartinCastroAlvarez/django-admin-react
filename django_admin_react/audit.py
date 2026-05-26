"""Access to Django's admin audit log (``LogEntry``).

This module is deliberately **outside** ``django_admin_react/api/``.
The ``api/`` package obeys the hard rule (``SECURITY.md`` §3 rule 10 /
``ACCEPTANCE.md`` §3.1 B-2): every **consumer-model** queryset starts
from ``ModelAdmin.get_queryset(request)``, never ``Model.objects.*``.

``django.contrib.admin.models.LogEntry`` is **not** a consumer model —
it is Django's own framework audit table, and Django's own
``ModelAdmin.history_view`` reads it via ``LogEntry.objects.filter(...)``
directly. The get_queryset rule is categorically inapplicable to it.
Keeping the LogEntry access here, in its own single-responsibility
module, makes that distinction explicit at the file-system level rather
than burying a special case inside the consumer-model API layer.

Public surface:

- :func:`object_log_entries` — the ``LogEntry`` queryset for one object,
  newest-first, with the acting user pre-fetched.
"""

from __future__ import annotations

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.db.models import QuerySet


def object_log_entries(obj: Model) -> QuerySet[LogEntry]:
    """Return the ``LogEntry`` rows for ``obj``, newest action first.

    Scoped by the object's ``ContentType`` + ``object_id`` — the same
    pair Django's admin ``history_view`` uses. ``select_related("user")``
    so the timeline serializer doesn't N+1 on the acting user.
    """
    content_type = ContentType.objects.get_for_model(type(obj))
    return (
        LogEntry.objects.filter(content_type=content_type, object_id=str(obj.pk))
        .select_related("user")
        .order_by("-action_time")
    )
