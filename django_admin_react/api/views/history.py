"""``GET /api/v1/<app>/<model>/<pk>/history/`` — object history.

Wire contract: ``docs/api-contract.md`` §4 (history sub-resource).

Surfaces the ``django.contrib.admin.models.LogEntry`` timeline for a
single object — the same data the legacy admin's *History* button
shows. Parity (#155): a Django dev's audit trail must be reachable
from the SPA, and the entries the SPA itself writes (via the create /
update / delete endpoints, which call ``ModelAdmin.log_*``) show up
here alongside any earlier HTML-admin entries.

Hard rules (`SECURITY.md` §3):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  Per-object ``has_view_permission`` gate — you can only read
           the history of an object you can view.
- Rule 10: Object loaded through ``ModelAdmin.get_queryset(request)``
           — never ``Model.objects.all()`` (B-2).
- CSRF:    GET is safe; no state change.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import DELETION
from django.contrib.admin.models import LogEntry
from django.core.paginator import Paginator
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import label_for
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import not_found_response
from django_admin_react.audit import object_log_entries

_ACTION_LABELS = {ADDITION: "addition", CHANGE: "change", DELETION: "deletion"}

_DEFAULT_PAGE_SIZE = 25
_MAX_PAGE_SIZE = 200


class HistoryView(View):
    """``GET /api/v1/<app_label>/<model_name>/<pk>/history/``."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Return the paginated ``LogEntry`` timeline for one object.

        Gates: ``is_admin_user`` → ``resolve_model`` → object loaded
        through ``get_queryset`` → ``has_view_permission(obj)``. A
        missing object or unviewable object both return the canonical
        404 (no oracle distinguishing "doesn't exist" from "you can't
        see it" — ``SECURITY.md`` §3 rule 12).
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        obj = load_object_or_none(model, model_admin, request, pk)
        if obj is None:
            return not_found_response()

        if not model_admin.has_view_permission(request, obj):
            return forbidden_response(request)

        entries = object_log_entries(obj)

        paginator = Paginator(entries, _page_size(request))
        page_number = _page_number(request)
        page = paginator.get_page(page_number)

        body = {
            "object": {"pk": obj.pk, "label": label_for(obj)},
            "entries": [_serialize_entry(e) for e in page.object_list],
            "page": page.number,
            "page_size": paginator.per_page,
            "total": paginator.count,
            "num_pages": paginator.num_pages,
        }
        response = JsonResponse(body, status=200)
        response["Cache-Control"] = "no-store"
        return response


def _serialize_entry(entry: LogEntry) -> dict[str, Any]:
    """One ``LogEntry`` → wire shape.

    ``change_message_human`` is Django's own rendered summary
    (``get_change_message``); ``change_message_structured`` is the raw
    JSON list so a SPA can render field-level detail without re-parsing
    the prose.
    """
    user = entry.user
    return {
        "id": entry.id,
        "action": _ACTION_LABELS.get(entry.action_flag, "unknown"),
        "action_time": entry.action_time.isoformat(),
        "user": None if user is None else {"id": entry.user_id, "label": str(user)},
        "change_message_human": entry.get_change_message(),
        "change_message_structured": _structured_message(entry),
    }


def _structured_message(entry: LogEntry) -> Any:
    """Return the raw structured change message, or ``[]`` if absent.

    ``LogEntry.change_message`` is a JSON string for entries written by
    modern admin; older / hand-written entries may store free text.
    ``get_change_message`` already handles the prose rendering, so here
    we only surface the structured form when it parses as a list.
    """
    import json

    raw = entry.change_message or ""
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _page_size(request: HttpRequest) -> int:
    """Clamp the ``page_size`` query param to ``[1, _MAX_PAGE_SIZE]``."""
    raw = request.GET.get("page_size")
    if raw is None:
        return _DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_PAGE_SIZE
    return max(1, min(value, _MAX_PAGE_SIZE))


def _page_number(request: HttpRequest) -> int:
    """Read the ``page`` query param; default 1 on absent / bogus."""
    raw = request.GET.get("page")
    if raw is None:
        return 1
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 1
