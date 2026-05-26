"""``PATCH /api/v1/<app>/<model>/<pk>/`` — partial update endpoint.

Wire contract: ``docs/api-contract.md`` §5.2.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_change_permission(request, obj)`` per-object gate.
- Rule 6:  Writes go through ``ModelAdmin.get_form()`` then
           ``save_model(..., change=True)`` (B-3).
- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)`` —
           never ``Model.objects.all()`` (B-2).
- Rule 12: Writes to ``readonly`` / ``exclude`` keys → 400 (S-31, B-3).
- CSRF:    No ``@csrf_exempt`` — Django's middleware enforces.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.views.detail import _build_payload
from django_admin_react.api.writes import form_errors_to_envelope
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import log_change
from django_admin_react.api.writes import merged_initial_for_update
from django_admin_react.api.writes import not_found_response
from django_admin_react.api.writes import parse_json_body
from django_admin_react.api.writes import readonly_or_excluded_names
from django_admin_react.api.writes import reject_forbidden_keys
from django_admin_react.api.writes import validation_failed
from django_admin_react.api.writes import writable_field_names


class UpdateView(View):
    """``PATCH /api/v1/<app_label>/<model_name>/<pk>/``."""

    http_method_names = ["patch"]

    def patch(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Partially update an instance (contract §5.2).

        PATCH semantics: any field the payload omits keeps its
        current value. The implementation builds form ``initial``
        data by overlaying the payload on the instance's current
        values, then runs ``ModelAdmin.get_form()`` exactly like the
        Django admin change view.

        Gates: ``is_admin_user`` → ``resolve_model`` →
        ``load_object_or_none`` (uses the admin's queryset, never
        ``Model.objects.all()``) → ``has_change_permission(request,
        obj)`` per-object gate (rule 5).

        Same payload-shape validation as create (unknown / readonly /
        excluded / sensitive keys → 400). Write path goes through
        ``form.save(commit=False)`` →
        ``model_admin.save_model(..., change=True)`` (rule 6 / B-3),
        wrapped in ``transaction.atomic()``.
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

        if not model_admin.has_change_permission(request, obj):
            return forbidden_response(request)

        parsed = parse_json_body(request)
        if isinstance(parsed, HttpResponse):
            return parsed
        payload: dict[str, Any] = parsed

        writable = writable_field_names(model, model_admin, request, obj)
        forbidden = readonly_or_excluded_names(model_admin, request, obj)
        rejection = reject_forbidden_keys(payload, writable, forbidden)
        if rejection is not None:
            return rejection

        form = model_admin.get_form(request, obj=obj)(
            data=merged_initial_for_update(obj, writable, payload, model),
            files=None,
            instance=obj,
        )
        if not form.is_valid():
            return validation_failed(form_errors_to_envelope(form))

        with transaction.atomic():
            instance = form.save(commit=False)
            model_admin.save_model(request, instance, form, change=True)
            form.save_m2m()
            log_change(model_admin, request, instance, form)

        response = JsonResponse(
            _build_payload(model, model_admin, instance, request),
            status=200,
        )
        response["Cache-Control"] = "no-store"
        return response
