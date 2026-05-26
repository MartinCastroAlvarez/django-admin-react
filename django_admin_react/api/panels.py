"""Per-model panel endpoint mixin (Issue #65).

Wire contract: ``docs/extensions.md`` §2.

Consumers register custom data endpoints under a model's detail URL
without re-implementing auth / model-resolution / permission gates.
Opt-in via the ``PanelEndpointsMixin`` on a ``ModelAdmin``:

::

    @admin.register(Invoice)
    class InvoiceAdmin(PanelEndpointsMixin, admin.ModelAdmin):
        panels = {"audit_trail": "get_audit_trail"}

        def get_audit_trail(self, request, obj):
            return {"entries": [...]}

URL shape: ``GET …/<app>/<model>/<pk>/panel/<name>/``

Hard rules (`SECURITY.md` §3):

- Rule 5: ``has_view_permission(request, obj)`` per-object gate.
- Rule 10: Object loaded via ``ModelAdmin.get_queryset(request)``.
- Rule 12: Unknown panel names → 404 (no oracle).
- Panel name is re-resolved through ``model_admin.panels`` — never
  used as a direct method lookup against the admin instance.
"""

from __future__ import annotations

from typing import Any
from typing import ClassVar

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import not_found_response


class PanelEndpointsMixin:
    """Opt-in mixin that declares custom panel endpoints on a ModelAdmin.

    Map panel names to method names on the admin (a string, not a
    callable, so the resolution path is auditable). Each method
    receives ``(self, request, obj)`` and returns a JSON-serialisable
    value.
    """

    panels: ClassVar[dict[str, str]] = {}


class PanelView(View):
    """``GET /api/v1/<app>/<model>/<pk>/panel/<panel_name>/``."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        panel_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        # Opt-in: admins that don't declare ``panels`` return 404 on
        # every panel URL.
        panels = getattr(model_admin, "panels", None) or {}
        if not isinstance(panels, dict) or panel_name not in panels:
            return not_found_response()

        method_name = panels[panel_name]
        # The handler name comes from the admin's own dict, not from
        # the URL — never let the URL pick a method directly.
        if not isinstance(method_name, str):
            return not_found_response()
        handler = getattr(model_admin, method_name, None)
        if not callable(handler):
            return not_found_response()

        obj = load_object_or_none(model, model_admin, request, pk)
        if obj is None:
            return not_found_response()
        if not model_admin.has_view_permission(request, obj):
            return forbidden_response(request)

        # The panel handler owns its own response shape. We surface
        # whatever JSON-serialisable value it returns. If it raises,
        # let it propagate to 500 — the consumer's handler is their
        # own surface and we don't want to mask their bug.
        result = handler(request, obj)
        response = JsonResponse({"panel": panel_name, "data": result}, status=200)
        response["Cache-Control"] = "no-store"
        return response
