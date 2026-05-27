"""``POST /api/v1/<app>/<model>/`` — create endpoint.

Wire contract: ``docs/api-contract.md`` §5.1.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 6:  Writes go through ``ModelAdmin.get_form()`` then
           ``save_model(..., change=False)`` (B-3).
- Rule 12: Unknown / readonly / excluded / sensitive payload keys → 400,
           never a silent drop.
- CSRF:    No ``@csrf_exempt`` — Django's middleware enforces.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError
from django.db import transaction
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import label_for
from django_admin_react.api.writes import coerce_fk_values
from django_admin_react.api.writes import conflict_response
from django_admin_react.api.writes import form_errors_to_envelope
from django_admin_react.api.writes import log_addition
from django_admin_react.api.writes import not_found_response
from django_admin_react.api.writes import parse_json_body
from django_admin_react.api.writes import readonly_or_excluded_names
from django_admin_react.api.writes import reject_forbidden_keys
from django_admin_react.api.writes import validation_failed
from django_admin_react.api.writes import writable_field_names


class CreateView(View):
    """``POST /api/v1/<app_label>/<model_name>/``."""

    http_method_names = ["post"]

    def post(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Create a new instance (contract §5.1).

        Gates: ``is_admin_user`` → ``resolve_model`` →
        ``has_add_permission(request)``. CSRF enforcement is Django's
        ``CsrfViewMiddleware`` — no ``@csrf_exempt`` (rule 4 /
        ACCEPTANCE §4.6 S-26).

        Payload validation runs **before** the form is built:

        - Unknown keys → 400 ``bad_request``.
        - Keys matching ``get_readonly_fields`` or ``get_exclude`` →
          400 (rule 12 / S-22, S-23).
        - Keys matching the sensitive-name denylist → 400 (S-31).

        The actual write goes through ``ModelAdmin.get_form()`` →
        ``form.save(commit=False)`` → ``model_admin.save_model(...)``
        — never ``setattr`` (rule 6 / B-3). Wrapped in
        ``transaction.atomic()``.
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

        parsed = parse_json_body(request)
        if isinstance(parsed, HttpResponse):
            return parsed
        payload: dict[str, Any] = parsed

        writable = writable_field_names(model, model_admin, request, obj=None)
        forbidden = readonly_or_excluded_names(model_admin, request, obj=None)
        rejection = reject_forbidden_keys(payload, writable, forbidden)
        if rejection is not None:
            return rejection

        form = model_admin.get_form(request, obj=None)(
            data=coerce_fk_values(payload, model),
            files=None,
        )
        if not form.is_valid():
            return validation_failed(form_errors_to_envelope(form))

        # A DB IntegrityError the form didn't catch (a uniqueness race, or a
        # DB-level constraint not mirrored in form validation) must exit the
        # atomic block before it's handled — catch outside (#404).
        try:
            with transaction.atomic():
                instance = form.save(commit=False)
                model_admin.save_model(request, instance, form, change=False)
                # Route M2M / related saves through ``save_related`` (not
                # ``form.save_m2m()`` directly) so a consumer's override is
                # honoured — Django's ``_changeform_view`` does the same
                # (Rule 1, #402). The default impl is ``form.save_m2m()`` +
                # a formset loop, so behaviour is unchanged when unoverridden.
                # No parent-level formsets on create yet (#403).
                model_admin.save_related(request, form, formsets=[], change=False)
                log_addition(model_admin, request, instance, form)
        except IntegrityError:
            return conflict_response()

        body = {
            "pk": instance.pk,
            "label": label_for(instance),
            "redirect": _redirect_for(
                request,
                model._meta.app_label,
                model._meta.model_name or "",
                instance.pk,
            ),
        }
        response = JsonResponse(body, status=201)
        response["Cache-Control"] = "no-store"
        return response


def _redirect_for(
    request: HttpRequest,
    app_label: str,
    model_name: str,
    pk: Any,
) -> str:
    """Construct a SPA-relative redirect (``<mount>/<app>/<model>/<pk>/``).

    The mount is reconstructed from the request path. The URL pattern
    is fixed inside this package, so everything in front of
    ``api/v1/`` is the consumer-chosen prefix
    (``ARCHITECTURE.md`` §4.5). Falls back to ``/`` if the pattern is
    not present (should not happen — the URL router routed us here).
    """
    suffix = "api/v1/"
    path = request.path
    idx = path.rfind(suffix)
    mount = path[:idx] if idx != -1 else "/"
    return f"{mount}{app_label}/{model_name}/{pk}/"
