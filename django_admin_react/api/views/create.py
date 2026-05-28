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

from django.core.exceptions import RequestDataTooBig
from django.core.exceptions import TooManyFieldsSent
from django.db import IntegrityError
from django.db import transaction
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.inlines_write import InlinePermissionDenied
from django_admin_react.api.inlines_write import InlineValidationError
from django_admin_react.api.inlines_write import apply_inline_writes
from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import label_for
from django_admin_react.api.writes import bad_request
from django_admin_react.api.writes import coerce_fk_values
from django_admin_react.api.writes import coerce_range_values
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

        # FileField / ImageField uploads arrive as multipart/form-data
        # (#241). Branch on content type: multipart feeds the ModelForm
        # ``request.POST`` (a QueryDict, so ``getlist`` preserves M2M) +
        # ``request.FILES``; JSON keeps the existing envelope path. CSRF is
        # enforced either way — ``CsrfViewMiddleware`` ran before this view
        # and there is no ``@csrf_exempt``.
        # Optional inline formsets (#403) — set only on the JSON path; a
        # multipart create (file uploads) doesn't carry inlines.
        inlines_payload: Any = None
        is_multipart = (request.content_type or "").startswith("multipart/form-data")
        if is_multipart:
            form_data: Any
            files: Any
            # Accessing request.POST/FILES triggers the multipart parse, which
            # enforces Django's body limits. Surface an over-limit upload as
            # the canonical JSON envelope instead of Django's default 400
            # page (#448) — RequestDataTooBig / TooManyFieldsSent are
            # SuspiciousOperation subclasses, not MultiPartParserError.
            try:
                form_data = request.POST
                files = request.FILES
            except (RequestDataTooBig, TooManyFieldsSent):
                return bad_request("Upload exceeds the configured size or field limits.")
            # Validate the union of POST + FILES keys: a file posted to a
            # readonly / excluded / unknown field is rejected just like a
            # scalar would be. Bare multipart values are not {id,label}
            # envelopes, so ``coerce_fk_values`` is skipped.
            submitted_keys: dict[str, Any] = dict.fromkeys(form_data)
            submitted_keys.update(dict.fromkeys(files))
        else:
            parsed = parse_json_body(request)
            if isinstance(parsed, HttpResponse):
                return parsed
            payload: dict[str, Any] = parsed
            # Strip the inline block before validating parent keys so it
            # isn't treated as an unknown field; it's saved after the parent.
            inlines_payload = payload.pop("inlines", None)
            form_data = coerce_range_values(coerce_fk_values(payload, model), model)
            files = None
            submitted_keys = payload

        writable = writable_field_names(model, model_admin, request, obj=None)
        forbidden = readonly_or_excluded_names(model_admin, request, obj=None)
        rejection = reject_forbidden_keys(submitted_keys, writable, forbidden)
        if rejection is not None:
            return rejection

        form = model_admin.get_form(request, obj=None)(data=form_data, files=files)
        if not form.is_valid():
            return validation_failed(form_errors_to_envelope(form))

        # A DB IntegrityError the form didn't catch (a uniqueness race, or a
        # DB-level constraint not mirrored in form validation) must exit the
        # atomic block before it's handled — catch outside (#404).
        try:
            with transaction.atomic():
                instance = form.save(commit=False)
                model_admin.save_model(request, instance, form, change=False)
                # Save M2M / related through the admin hook (#402), not a
                # bare form.save_m2m(), so a consumer's save_related override
                # is honoured. The default save_related just runs save_m2m;
                # inline formsets flow through our own write path, so the
                # `formsets` list is empty here.
                model_admin.save_related(request, form, [], change=False)
                log_addition(model_admin, request, instance, form)
                # Inline formsets (#403) round-trip in the SAME transaction
                # as the parent create, so a child permission denial or a
                # formset validation failure reverts the parent too — exactly
                # how the update endpoint handles them.
                if inlines_payload is not None:
                    inline_errors = apply_inline_writes(
                        model_admin, request, instance, form, inlines_payload
                    )
                    if inline_errors is not None:
                        raise InlineValidationError(inline_errors)
        except InlinePermissionDenied:
            return forbidden_response(request)
        except InlineValidationError as exc:
            return validation_failed({"inlines": exc.errors})
        except IntegrityError:
            return conflict_response()
        except ValueError:
            # Malformed `inlines` payload shape (not a 500) — fixed generic
            # message, never echoing exception text (CodeQL stack-trace).
            return bad_request("Malformed 'inlines' payload.")

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
