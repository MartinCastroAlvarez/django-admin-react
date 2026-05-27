"""``GET /api/v1/recent-actions/`` — the current user's recent actions.

Mirrors Django admin's index "Recent actions" panel: the signed-in
user's own last few ``LogEntry`` rows, newest first, each linking to
the affected object's change page when that object is still reachable.

Like the rest of the API this is staff-gated and ``Cache-Control:
no-store``. It is scoped to ``request.user`` — a user only ever sees
their own action log, never anyone else's (``SECURITY.md`` §3 rule 12).
The link target is gated by the target model's admin registration +
view permission, so the panel never links into a 403/404.
"""

from __future__ import annotations

from typing import Any
from typing import cast

from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import DELETION
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.audit import user_log_entries

# Default / ceiling for the number of entries returned. Django's index
# shows 10; the ceiling keeps a hand-crafted ``?limit=`` from scanning
# the whole table.
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 100

_ACTION_LABELS: dict[int, str] = {
    ADDITION: "added",
    CHANGE: "changed",
    DELETION: "deleted",
}


class RecentActionsView(View):
    """Return the signed-in user's recent admin actions (index parity)."""

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """The current user's last ``limit`` ``LogEntry`` rows.

        Gate: ``is_admin_user`` (staff + ``AdminSite.has_permission``).
        Scoped to ``request.user`` — no cross-user leakage.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        # ``is_admin_user`` guarantees an authenticated user, so pk is set
        # (it may be int or str for a custom user model — both are valid
        # lookups). The LogEntry query lives in ``django_admin_react.audit``
        # (outside ``api/``): LogEntry is Django's own audit table, not a
        # consumer model, so the get_queryset rule is inapplicable — and
        # keeping ``.objects.filter`` out of ``api/`` honours SECURITY §3
        # rule 10 at the file-system level (see audit.py + test_s15).
        user_pk = cast("str | int", request.user.pk)
        entries = user_log_entries(user_pk, _limit(request))
        body = {"actions": [_serialize_action(e, admin_site, request) for e in entries]}
        response = JsonResponse(body, status=200)
        response["Cache-Control"] = "no-store"
        return response


def _serialize_action(entry: LogEntry, admin_site: Any, request: HttpRequest) -> dict[str, Any]:
    """One ``LogEntry`` → recent-actions wire shape.

    ``object_repr`` is what the user saw when they performed the action
    (Django stores it on the row), so it is safe to echo back even for a
    now-deleted object. ``target`` is the navigable change-page locator,
    or ``null`` when the object can't be linked (deleted, unregistered
    model, or no view permission) — the SPA then renders plain text.
    """
    return {
        "id": entry.id,
        "action": _ACTION_LABELS.get(entry.action_flag, "unknown"),
        "action_time": entry.action_time.isoformat(),
        "object_repr": entry.object_repr,
        "target": _target_for(entry, admin_site, request),
    }


def _target_for(
    entry: LogEntry, admin_site: Any, request: HttpRequest
) -> dict[str, Any] | None:
    """Change-page locator for the entry's object, or ``None``.

    Returns ``None`` for deletions (no live object), for content types
    whose model can't be resolved, for models not registered on the
    admin site, and when the user lacks module / view permission — so
    the SPA never offers a link that would 403 or 404.
    """
    if entry.action_flag == DELETION:
        return None
    ct_id = entry.content_type_id
    if ct_id is None:
        return None
    try:
        content_type = ContentType.objects.get_for_id(ct_id)
    except ContentType.DoesNotExist:
        return None
    model = content_type.model_class()
    if model is None:
        return None
    model_admin = admin_site._registry.get(model)
    if model_admin is None:
        return None
    if not model_admin.has_module_permission(request):
        return None
    if not model_admin.has_view_permission(request):
        return None
    meta = model._meta
    return {
        "app_label": meta.app_label,
        "model_name": meta.model_name,
        "pk": entry.object_id,
    }


def _limit(request: HttpRequest) -> int:
    """Clamp the ``limit`` query param to ``[1, _MAX_LIMIT]``."""
    raw = request.GET.get("limit")
    if raw is None:
        return _DEFAULT_LIMIT
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT
    return max(1, min(value, _MAX_LIMIT))
