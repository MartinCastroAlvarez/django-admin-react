"""GET /api/v1/registry/ — apps and models the user may see.

Wire contract: ``docs/api-contract.md`` §2.

Implementation rules followed (`SECURITY.md` §3):

- Rule 1:  Default permission gate is staff + ``AdminSite.has_permission``.
- Rule 3:  Models come exclusively from the configured admin site's
           ``_registry`` — we never look at the global app registry.
- Rule 5:  ``ModelAdmin.has_module_permission`` and ``has_view_permission``
           decide visibility; we never invent our own gate.
- Rule 10: No ``Model.objects.all()`` is ever called from this view —
           it doesn't read any model data at all.
- Rule 12: Failures return 403 with an opaque body, never 404.
"""

from __future__ import annotations

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import build_registry_payload
from django_admin_react.api.registry import get_admin_site


class RegistryView(View):
    """``GET /api/v1/registry/`` — registry of visible apps and models."""

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:  # noqa: ARG002
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response()
        response = JsonResponse(build_registry_payload(admin_site, request), status=200)
        # Never let an intermediate proxy or browser cache cross-user
        # data (extends ACCEPTANCE.md §4.6 S-30 to 200 responses).
        response["Cache-Control"] = "no-store"
        return response
