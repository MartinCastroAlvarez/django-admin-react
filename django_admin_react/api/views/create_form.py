"""``GET /api/v1/<app>/<model>/add/`` — the create-form schema.

The detail view (``/<pk>/``) needs an existing object; the SPA's
create page needs the same field descriptors + fieldsets for a *new*
object. This view builds that payload from an unsaved instance, the
add form (``get_form(request, obj=None, change=False)`` — exactly how
Django's add view builds it), and the read-visible field set.

It deliberately reuses the detail view's descriptor builders so the
field shape is byte-for-byte identical to what edit renders — the SPA
uses one ``FieldInput`` component for both.

Hard rules: staff gate (rule 1), model resolved through the registry
(rule 3), ``has_add_permission`` gate (rule 6 — create is gated on
add, not view), sensitive-name denylist applied (S-31).
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
from django_admin_react.api.registry import save_options
from django_admin_react.api.views.detail import _descriptor_for
from django_admin_react.api.views.detail import _fieldsets_payload
from django_admin_react.api.views.detail import _visible_field_names
from django_admin_react.api.writes import not_found_response


class AddFormView(View):
    """``GET /api/v1/<app_label>/<model_name>/add/`` — empty create form."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
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

        # Create is gated on add — not view. A user who can view but
        # not add must not be handed an add form.
        if not model_admin.has_add_permission(request):
            return forbidden_response(request)

        # Unsaved instance so descriptor builders have field defaults to
        # read (FK → None, M2M → [] via the guards in _descriptor_for).
        obj = model()

        visible_names = _visible_field_names(model_admin, request, None)
        readonly = set(model_admin.get_readonly_fields(request, None) or ())
        # The ADD form — change=False, obj=None — exactly how Django's
        # add view constructs it (``ModelAdmin._changeform_view`` with
        # add=True passes change=False).
        form = model_admin.get_form(request, obj=None, change=False)()

        fields: dict[str, dict[str, Any]] = {}
        for name in visible_names:
            fields[name] = _descriptor_for(
                model=model,
                model_admin=model_admin,
                obj=obj,
                name=name,
                form=form,
                is_readonly=name in readonly,
                admin_site=admin_site,
            )

        payload = {
            "app_label": model._meta.app_label,
            "model_name": model._meta.model_name,
            "permissions": model_permissions(model_admin, request),
            "fieldsets": _fieldsets_payload(model_admin, request, None, visible_names),
            "fields": fields,
            # Add-view save-flow buttons (#154): obj=None → add semantics
            # (Save / Save-and-add-another / Save-and-continue editing).
            "save_options": save_options(model_admin, request, None),
        }
        response = JsonResponse(payload, status=200)
        response["Cache-Control"] = "no-store"
        return response
