"""``GET /api/v1/recent-actions/`` — the requesting user's activity feed.

Wire contract: ``docs/api-contract.md`` §2.1 (recent-actions sub-resource).

Django's admin **index page** renders a *"Recent actions"* sidebar — the
current user's last few ``LogEntry`` rows across **all** models
(``AdminSite.index`` → ``get_admin_log`` →
``LogEntry.objects.filter(user=request.user)``). The SPA replaces the
index, so without this endpoint a Django dev who relies on that panel
loses it — a parity regression (#502).

Unlike the per-object history sub-resource (``history.py``), this is an
index-level, **per-user** feed: it is keyed on the acting user, not on a
model/object, so it mounts on a reserved single-segment prefix alongside
``registry`` / ``schema`` rather than under ``<app>/<model>/``.

Hard rules (`SECURITY.md` §3):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate, identical to every
           other read endpoint.
- Rule 5:  Deep-links are resolved through the admin registry +
           ``has_view_permission`` (via :func:`resolve_model`); an entry
           whose target the user can't view is still listed (Django lists
           it) but with **no link** — never mint a URL to a forbidden or
           unreachable page (least disclosure).
- CSRF:    GET is safe; no state change. ``Cache-Control: no-store`` so a
           per-user feed is never cached by an intermediate proxy.

The **per-user scope is the security boundary**: the underlying query
(:func:`user_log_entries`) filters strictly on ``user=request.user``, so
the feed can never surface who-changed-what for other users.
"""

from __future__ import annotations

from typing import Any
from typing import cast

from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import DELETION
from django.contrib.admin.models import LogEntry
from django.contrib.admin.sites import AdminSite
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.audit import user_log_entries

_ACTION_LABELS = {ADDITION: "addition", CHANGE: "change", DELETION: "deletion"}

_DEFAULT_LIMIT = 10
_MAX_LIMIT = 100


class RecentActionsView(View):
    """``GET /api/v1/recent-actions/`` — the user's own recent actions."""

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:  # noqa: ARG002
        """Return the requesting user's recent ``LogEntry`` feed.

        Gate: ``is_admin_user`` (rule 1) → 403 envelope otherwise. The
        rows come from :func:`user_log_entries`, which applies the
        mandatory ``user_id=request.user.pk`` filter; each entry's
        deep-link is gated independently by :func:`_serialize_entry`.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        limit = _limit(request)
        entries = user_log_entries(request.user.pk, limit)
        body = {
            "entries": [_serialize_entry(e, admin_site, request) for e in entries],
            "limit": limit,
        }
        response = JsonResponse(body, status=200)
        response["Cache-Control"] = "no-store"
        return response


def _serialize_entry(
    entry: LogEntry, admin_site: AdminSite, request: HttpRequest
) -> dict[str, Any]:
    """One ``LogEntry`` → wire shape for the recent-actions feed.

    ``object_repr`` is the label Django stored when the action happened
    (the user already saw it), so surfacing it leaks nothing new.
    ``content_type`` carries the app/model labels for display — present
    even when the target model is unregistered or its class is gone
    (matching Django, which still lists the entry). ``link`` is the
    deep-link target, or ``None`` when the object can't be safely linked
    (see :func:`_link`).
    """
    content_type = _content_type_payload(entry)
    return {
        "id": entry.id,
        "action": _ACTION_LABELS.get(entry.action_flag, "unknown"),
        "action_time": entry.action_time.isoformat(),
        "object_repr": entry.object_repr,
        "content_type": content_type,
        "link": _link(entry, admin_site, request),
    }


def _content_type_payload(entry: LogEntry) -> dict[str, str] | None:
    """App/model labels for the entry's content type, or ``None``.

    ``ContentType.name`` falls back to the raw model string when the
    model class no longer exists (a deleted/renamed model), so this never
    raises on a stale content type.
    """
    # The django-stubs ``LogEntry`` stub types ``content_type`` as a bare
    # ``ForeignKey``; narrow to the runtime type so attribute access checks.
    content_type = cast("ContentType | None", entry.content_type)
    if content_type is None:
        return None
    return {
        "app_label": content_type.app_label,
        "model": content_type.model,
        "name": str(content_type.name),
    }


def _link(entry: LogEntry, admin_site: AdminSite, request: HttpRequest) -> dict[str, str] | None:
    """Resolve a safe deep-link to the entry's object, or ``None``.

    Returns ``None`` — i.e. renders as label-only text, like Django — when:

    - the action is a **deletion** (the object no longer exists);
    - the entry has no content type or no object id;
    - the target model isn't registered in the admin site, or the user
      lacks ``has_view_permission`` for it (resolved via
      :func:`resolve_model`, which applies the module + view gates).

    Only when all checks pass do we surface ``{app_label, model_name, pk}``
    for the SPA to build its detail URL — never a raw URL to a page the
    user can't open.
    """
    if entry.action_flag == DELETION:
        return None
    content_type = cast("ContentType | None", entry.content_type)
    if content_type is None or not entry.object_id:
        return None
    resolved = resolve_model(admin_site, request, content_type.app_label, content_type.model)
    if resolved is None:
        return None
    return {
        "app_label": content_type.app_label,
        "model_name": content_type.model,
        "pk": str(entry.object_id),
    }


def _limit(request: HttpRequest) -> int:
    """Clamp the ``limit`` query param to ``[1, _MAX_LIMIT]``.

    Absent or non-integer values fall back to ``_DEFAULT_LIMIT`` (10,
    matching Django's index panel).
    """
    raw = request.GET.get("limit")
    if raw is None:
        return _DEFAULT_LIMIT
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT
    return max(1, min(value, _MAX_LIMIT))
