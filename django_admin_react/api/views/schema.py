"""``GET /api/v1/schema/`` — OpenAPI 3.1 wire-shape spec (issue #64).

Wire contract: ``docs/api-contract.md`` §12.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Cache:  ``no-store``. The spec itself is static, but the gate
          guarantees per-user authorization (a 403 from a logged-out
          browser must not be cached and served as a 200 next time).

Why staff-gated:

- The spec describes the *shape* of the API, not its *contents* —
  but discovering the wire shape is valuable input to a directed
  attack. Keeping behind the same gate as the rest of the API
  (rather than public) costs nothing and removes one rung from any
  reconnaissance ladder.
- Public docs already live at ``docs/api-contract.md``; consumers who
  want an unauthenticated reference go there.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.schema import openapi_spec


class SchemaView(View):
    """``GET /api/v1/schema/`` — the OpenAPI 3.1 document."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Return the OpenAPI 3.1 spec as ``application/json``.

        Gates:

        1. ``is_admin_user`` — staff session + ``AdminSite.has_permission``.
           No leak: pre-auth callers get the standard 403 envelope.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response()

        response = JsonResponse(openapi_spec(), status=200)
        # No-store: even though the document is static, the gate is
        # per-request and we never want a logged-out 403 to be served
        # as a cached 200 by an intermediary.
        response["Cache-Control"] = "no-store"
        return response
