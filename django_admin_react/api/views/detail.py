"""GET /api/v1/<app>/<model>/<pk>/ — detail view.

Wire contract: ``docs/api-contract.md`` §4.

Rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_view_permission(request, obj)`` per-object gate.
- Rule 6:  Fields come from ``ModelAdmin.get_form(request, obj)`` /
           ``get_fields`` / ``get_readonly_fields`` / ``get_exclude``.
           Sensitive-name denylist applied on top
           (``ACCEPTANCE.md`` §4.7 S-31).
- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)``
           — never ``Model.objects.all()`` (B-2).
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.utils import label_for_field
from django.db.models import ForeignKey
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
from django_admin_react.api.serializers import field_metadata
from django_admin_react.api.serializers import filter_sensitive
from django_admin_react.api.serializers import is_sensitive_field_name
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value

_NOT_FOUND_BODY: dict[str, dict[str, str]] = {
    "error": {"code": "not_found", "message": "Not found."}
}


def _not_found_response() -> HttpResponse:
    response = JsonResponse(_NOT_FOUND_BODY, status=404)
    response["Cache-Control"] = "no-store"
    return response


class DetailView(View):
    """``GET /api/v1/<app_label>/<model_name>/<pk>/`` — single object."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response()

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return _not_found_response()
        model, model_admin = resolved

        try:
            obj = model_admin.get_queryset(request).get(pk=pk)
        except model.DoesNotExist:
            return _not_found_response()
        except (ValueError, TypeError):
            # Bogus pk (e.g., non-int against IntegerField) → 404, never 500.
            return _not_found_response()

        if not model_admin.has_view_permission(request, obj):
            return forbidden_response()

        payload = _build_payload(model, model_admin, obj, request)
        response = JsonResponse(payload, status=200)
        # No-store: per-user, permission-gated payload must never be
        # cached by intermediate proxies or the browser. Extends
        # ACCEPTANCE.md §4.6 S-30 (defined for 4xx) to 200 responses.
        response["Cache-Control"] = "no-store"
        return response


def _build_payload(
    model: type[Model],
    model_admin: ModelAdmin,
    obj: Model,
    request: HttpRequest,
) -> dict[str, Any]:
    visible_names = _visible_field_names(model, model_admin, request, obj)
    fieldsets_payload = _fieldsets_payload(model_admin, request, obj, visible_names)
    fields_payload = _fields_payload(model, model_admin, obj, request, visible_names)
    return {
        "app_label": model._meta.app_label,
        "model_name": model._meta.model_name,
        "pk": obj.pk,
        "label": _label_for(obj),
        "permissions": model_permissions(model_admin, request),
        "fieldsets": fieldsets_payload,
        "fields": fields_payload,
    }


def _visible_field_names(
    model: type[Model],
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model,
) -> list[str]:
    """Compute the set of field names the API may surface for this object."""
    declared = list(model_admin.get_fields(request, obj) or ())
    excluded = set(model_admin.get_exclude(request, obj) or ())
    visible: list[str] = []
    for name in declared:
        if name in excluded:
            continue
        if is_sensitive_field_name(name):
            continue
        visible.append(name)
    return filter_sensitive(visible)


def _fieldsets_payload(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model,
    visible_names: list[str],
) -> list[dict[str, Any]]:
    visible_set = set(visible_names)
    try:
        raw = model_admin.get_fieldsets(request, obj) or ()
    except Exception:
        raw = ()
    if not raw:
        return [{"title": None, "fields": visible_names}]

    payload: list[dict[str, Any]] = []
    for title, opts in raw:
        fields = []
        for entry in opts.get("fields", ()):
            if isinstance(entry, list | tuple):
                for sub in entry:
                    if sub in visible_set:
                        fields.append(sub)
            elif entry in visible_set:
                fields.append(entry)
        if fields:
            payload.append({"title": title, "fields": fields})
    if not payload:
        return [{"title": None, "fields": visible_names}]
    return payload


def _fields_payload(
    model: type[Model],
    model_admin: ModelAdmin,
    obj: Model,
    request: HttpRequest,
    visible_names: list[str],
) -> dict[str, dict[str, Any]]:
    readonly = set(model_admin.get_readonly_fields(request, obj) or ())
    form_class = model_admin.get_form(request, obj=obj)
    form = form_class(instance=obj)

    out: dict[str, dict[str, Any]] = {}
    for name in visible_names:
        is_readonly = name in readonly
        model_field = _safe_get_field(model, name)
        if model_field is None:
            # Pure readonly callable / method.
            value = getattr(obj, name, None)
            if callable(value):
                try:
                    value = value()
                except Exception:
                    value = None
            out[name] = {
                "type": "unsupported",
                "label": _label(model_admin, model, name),
                "required": False,
                "readonly": True,
                "help_text": "",
                "value": serialize_value(value),
            }
            continue

        if isinstance(model_field, ForeignKey):
            value: Any = serialize_fk_value(getattr(obj, name, None))
        else:
            value = serialize_value(getattr(obj, name, None))

        form_field = form.fields.get(name)
        required = bool(form_field.required) if form_field is not None else False
        help_text = getattr(model_field, "help_text", "") or (
            form_field.help_text if form_field is not None else ""
        )

        out[name] = field_metadata(
            model_field,
            label=_label(model_admin, model, name),
            required=required,
            readonly=is_readonly,
            help_text=str(help_text),
            value=value,
        )
    return out


def _safe_get_field(model: type[Model], name: str):
    try:
        return model._meta.get_field(name)
    except Exception:
        return None


def _label(model_admin: ModelAdmin, model: type[Model], name: str) -> str:
    try:
        return str(label_for_field(name, model, model_admin))
    except Exception:
        return name


def _label_for(obj: Model) -> str:
    try:
        return str(obj)
    except Exception:  # pragma: no cover
        return f"<{obj.__class__.__name__}: {obj.pk}>"
