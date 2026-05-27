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
                request=request,
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
            # prepopulated_fields (#245): {target: [sources]} so the SPA can
            # slugify the target from its sources while typing — Django's
            # add-form behaviour. Restrict to fields actually rendered, and
            # never a readonly target (it can't be filled), mirroring how
            # Django drops readonly targets from the change-form JS.
            "prepopulated_fields": _prepopulated_payload(
                model_admin, request, visible_names, readonly
            ),
            # Add-form initial values (#444): ModelAdmin.get_changeform_initial_data
            # (GET-param prefill — "add another, prefilled from a link"),
            # filtered to the visible, non-readonly fields. The SPA seeds the
            # form; the write still re-validates through the form +
            # reject_forbidden_keys, so prefill is a hint, never a gate bypass.
            "initial": _initial_payload(model_admin, request, visible_names, readonly),
        }
        response = JsonResponse(payload, status=200)
        response["Cache-Control"] = "no-store"
        return response


def _prepopulated_payload(
    model_admin: Any,
    request: HttpRequest,
    visible_names: list[str],
    readonly: set[str],
) -> dict[str, list[str]]:
    """Build the ``prepopulated_fields`` block (#245).

    Returns ``{target: [sources]}`` from ``ModelAdmin.prepopulated_fields``,
    restricted to fields actually rendered: a target that's readonly or not
    in the form is dropped (it can't be filled), and source names the form
    doesn't render are filtered out. A target left with no usable sources is
    omitted. The SPA slugifies the target from its sources while typing.
    """
    try:
        raw = model_admin.get_prepopulated_fields(request, None) or {}
    except Exception:  # pragma: no cover — admin author error
        return {}
    visible = set(visible_names)
    out: dict[str, list[str]] = {}
    for target, sources in raw.items():
        if target not in visible or target in readonly:
            continue
        kept = [s for s in sources if s in visible]
        if kept:
            out[target] = kept
    return out


def _initial_payload(
    model_admin: Any,
    request: HttpRequest,
    visible_names: list[str],
    readonly: set[str],
) -> dict[str, Any]:
    """Build the add-form ``initial`` block (#444).

    Values come from ``ModelAdmin.get_changeform_initial_data(request)`` —
    Django's GET-param prefill ("add another, prefilled from a link").
    Filtered to the visible, non-readonly fields so an arbitrary GET key, a
    readonly field, or a sensitive-name field (already dropped from
    ``visible_names``) is never echoed back. Values are JSON-coerced
    defensively (a consumer override could return a non-serialisable value).
    Always a hint: the actual write re-validates through the form.
    """
    try:
        raw = model_admin.get_changeform_initial_data(request) or {}
    except Exception:  # pragma: no cover — admin author error
        return {}
    allowed = set(visible_names) - set(readonly)
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key in allowed:
            out[key] = _json_safe(value)
    return out


def _json_safe(value: Any) -> Any:
    """Coerce a prefill value to a JSON-serialisable form (#444)."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [
            v if v is None or isinstance(v, str | int | float | bool) else str(v) for v in value
        ]
    return str(value)
