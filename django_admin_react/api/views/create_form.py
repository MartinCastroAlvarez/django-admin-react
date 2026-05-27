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

from django.core.exceptions import ValidationError
from django.db.models import FileField
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model
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
from django_admin_react.api.serializers import safe_get_field
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value
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
        # Initial overlay (#444): Django's add view seeds the form with
        # ``get_changeform_initial_data(request)`` — which, by default,
        # reflects ``request.GET`` so a link like ``/add/?status=open``
        # (and the "save and add another" prefill) lands pre-filled, and
        # which a ModelAdmin may override. Build the form with that
        # initial, exactly how ``_changeform_view`` does.
        initial = _changeform_initial(model_admin, request)
        # The ADD form — change=False, obj=None — exactly how Django's
        # add view constructs it (``ModelAdmin._changeform_view`` with
        # add=True passes change=False).
        form = model_admin.get_form(request, obj=None, change=False)(initial=initial)

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

        # Overlay the initial values onto the descriptors. Done as a
        # second pass (rather than mutating ``obj``) so the shared
        # descriptor builder stays untouched and a bad initial can never
        # 500 the form: each value is coerced through the add-form's own
        # field, so FKs resolve against the admin-scoped ``ModelChoiceField``
        # queryset (rule 2) and an invalid initial is simply ignored.
        _overlay_initial(fields, model, form, initial, admin_site, request)

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
        }
        response = JsonResponse(payload, status=200)
        response["Cache-Control"] = "no-store"
        return response


def _changeform_initial(model_admin: Any, request: HttpRequest) -> dict[str, Any]:
    """Return ``get_changeform_initial_data(request)`` as a safe dict (#444).

    Django's default reads ``request.GET`` (so ``?field=value`` links
    prefill) and an admin may override it to inject defaults. A buggy
    override must not 500 the form, so a non-dict or a raised exception
    degrades to "no prefill".
    """
    try:
        data = model_admin.get_changeform_initial_data(request)
    except Exception:  # pragma: no cover — admin author error
        return {}
    return data if isinstance(data, dict) else {}


def _overlay_initial(
    fields: dict[str, dict[str, Any]],
    model: type[Model],
    form: Any,
    initial: dict[str, Any],
    admin_site: Any,
    request: HttpRequest,
) -> None:
    """Overlay add-form initial values onto the field descriptors (#444).

    Only fields that are both rendered (in ``fields``) and present in the
    add form are touched — an initial for an excluded/sensitive field is
    ignored, since that field isn't in the payload to begin with. Each
    value is coerced through the form field's ``to_python`` so it matches
    exactly what Django would render into the widget:

    - FK → the form's ``ModelChoiceField.queryset`` resolves the pk to an
      instance (admin-scoped, rule 2), serialized as the ``{id, label}``
      envelope; an unknown/invalid pk raises and is ignored (no 500).
    - scalar / choice / bool / date → coerced and re-serialized in place.
    - M2M / File → skipped: neither is meaningfully settable on the
      unsaved add instance, and GET-param prefill of them is not a thing
      Django's add view does either.

    Any coercion error leaves the field's default value untouched.
    """
    for name, raw in initial.items():
        descriptor = fields.get(name)
        if descriptor is None:
            continue
        field = safe_get_field(model, name)
        form_field = form.fields.get(name)
        if field is None or form_field is None:
            continue
        if isinstance(field, ManyToManyField | FileField):
            continue
        # Coercion failures (a bad FK pk, an unparseable date) are the
        # expected outcome of a hand-crafted prefill URL — narrow the
        # catch to what ``to_python`` raises so a real bug still surfaces,
        # and leave the field's default value in place.
        try:
            if isinstance(field, ForeignKey):
                related = form_field.to_python(raw)
                descriptor["value"] = serialize_fk_value(
                    related, admin_site=admin_site, request=request
                )
            else:
                descriptor["value"] = serialize_value(form_field.to_python(raw), field=field)
        except (ValidationError, ValueError, TypeError):
            continue


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
