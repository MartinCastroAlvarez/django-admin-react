"""``GET /api/v1/<app>/<model>/add/`` — blank create-form metadata.

Wire contract: ``docs/api-contract.md`` §5.1 (create-form metadata).

The SPA's create page needs the field + fieldset descriptors for a
**new** object before the user has typed anything — the detail endpoint
can't serve that (it requires a pk). This endpoint returns the same
shape as the detail response's form half, built with ``obj=None`` and
``change=False`` (Django's add-form path), gated by
``has_add_permission``. It unblocks the create flow (#181).

Hard rules (`SECURITY.md` §3):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 6:  Fields come from ``ModelAdmin.get_form(request, obj=None,
           change=False)`` / ``get_fieldsets`` — never a parallel
           field source.
- CSRF:    GET is safe; this endpoint never writes.
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
from django_admin_react.api.registry import model_permissions
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.views.detail import _fields_payload
from django_admin_react.api.views.detail import _fieldsets_payload
from django_admin_react.api.views.detail import _visible_field_names
from django_admin_react.api.writes import not_found_response


class AddFormView(View):
    """``GET /api/v1/<app_label>/<model_name>/add/``."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Return the blank add-form metadata (fields + fieldsets).

        Gates: ``is_admin_user`` → ``resolve_model`` →
        ``has_add_permission(request)``. Mirrors the detail response's
        form half but for ``obj=None`` (``change=False``), so the SPA
        renders the create form identically to the edit form.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        if not model_admin.has_add_permission(request):
            return forbidden_response(request)

        visible_names = _visible_field_names(model_admin, request, None)
        body = {
            "app_label": model._meta.app_label,
            "model_name": model._meta.model_name,
            "permissions": model_permissions(model_admin, request),
            "fieldsets": _fieldsets_payload(model_admin, request, None, visible_names),
            "fields": _fields_payload(
                model, model_admin, None, request, visible_names, change=False
            ),
        }
        response = JsonResponse(body, status=200)
        response["Cache-Control"] = "no-store"
        return response
