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
- :func:`user_log_entries` — the requesting user's own recent
  ``LogEntry`` rows across all models (the admin index "Recent actions"
  feed), newest-first, with each entry's content type pre-fetched.
"""

from __future__ import annotations

from typing import Any

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


def user_log_entries(user_pk: Any, limit: int) -> list[LogEntry]:
    """Return the ``LogEntry`` rows for ``user_pk``, newest first.

    Mirrors Django's admin index "Recent actions" panel
    (``AdminSite.index`` → ``get_admin_log`` →
    ``LogEntry.objects.filter(user=request.user)``).
    ``select_related("content_type")`` so the feed serializer doesn't N+1
    resolving each entry's model labels.

    The ``user_id`` filter is the **security boundary** (issue #502): the
    feed is a personal activity log and must never surface another user's
    actions. It is applied unconditionally here so no caller can forget
    it. ``user_pk`` is typed ``Any`` because the acting user's primary key
    varies by user model (int / UUID / str); callers must gate the request
    first and pass an authenticated user's ``pk``. ``limit`` is sliced in
    the database (it is already clamped by the view).
    """
    return list(
        LogEntry.objects.filter(user_id=user_pk)
        .select_related("content_type")
        .order_by("-action_time")[:limit]
    )
