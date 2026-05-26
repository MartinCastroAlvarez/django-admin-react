"""``GET /api/v1/<app>/<model>/<pk>/`` — single-object detail view.

Wire contract: ``docs/api-contract.md`` §4.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_view_permission(request, obj)`` per-object gate.
- Rule 6:  Fields come from ``ModelAdmin.get_form(request, obj)`` /
           ``get_fields`` / ``get_readonly_fields`` / ``get_exclude``.
           Sensitive-name denylist applied on top
           (``ACCEPTANCE.md`` §4.7 S-31).
- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)`` —
           never ``Model.objects.all()`` (B-2).
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.utils import label_for_field
from django.db.models import FileField
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.inlines import inlines_payload
from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import model_permissions
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.registry import save_options
from django_admin_react.api.serializers import field_metadata
from django_admin_react.api.serializers import filter_sensitive
from django_admin_react.api.serializers import is_sensitive_field_name
from django_admin_react.api.serializers import label_for
from django_admin_react.api.serializers import safe_get_field
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import not_found_response


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
        """Return the full descriptor for one object (contract §4).

        Gates, in order:

        1. ``is_admin_user`` — 403 if not authenticated active staff.
        2. ``resolve_model`` — 404 if model unknown or unviewable.
        3. ``load_object_or_none`` — 404 if pk doesn't resolve under
           the admin's queryset (rule 10) or parse-fails.
        4. ``has_view_permission(request, obj)`` — per-object gate
           (rule 5); 403 once we know the object exists but the user
           may not see *this* row.

        The payload includes the visible field set, fieldsets, the
        four ``has_*_permission`` booleans, and a friendly label.
        Excluded / readonly / sensitive-named fields are dropped by
        the visibility filter (defense in depth on top of the admin
        form).
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

        if not model_admin.has_view_permission(request, obj):
            return forbidden_response(request)

        payload = _build_payload(model, model_admin, obj, request)
        response = JsonResponse(payload, status=200)
        # No-store: per-user, permission-gated payload must never be
        # cached by intermediate proxies or the browser. Extends
        # ACCEPTANCE.md §4.6 S-30 (defined for 4xx) to 200 responses.
        response["Cache-Control"] = "no-store"
        return response


# --------------------------------------------------------------------------- #
# Payload assembly                                                            #
# --------------------------------------------------------------------------- #
def _build_payload(
    model: type[Model],
    model_admin: ModelAdmin,
    obj: Model,
    request: HttpRequest,
) -> dict[str, Any]:
    """Compose the full detail response body (contract §4)."""
    visible_names = _visible_field_names(model_admin, request, obj)
    return {
        "app_label": model._meta.app_label,
        "model_name": model._meta.model_name,
        "pk": obj.pk,
        "label": label_for(obj),
        "permissions": model_permissions(model_admin, request),
        "save_options": save_options(model_admin, request, obj),
        "fieldsets": _fieldsets_payload(model_admin, request, obj, visible_names),
        "fields": _fields_payload(model, model_admin, obj, request, visible_names),
        "inlines": inlines_payload(model_admin, obj, request),
    }


def _visible_field_names(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model,
) -> list[str]:
    """Field names the detail response may surface for this object.

    This is the *read*-visible set: it includes readonly fields (so
    the UI can render them) but drops admin-excluded fields and any
    name matching the sensitive denylist. The *writable* set (for
    POST/PATCH) lives in ``writes.writable_field_names`` and is
    narrower.
    """
    declared = list(model_admin.get_fields(request, obj) or ())
    excluded = set(model_admin.get_exclude(request, obj) or ())
    visible = [
        name for name in declared if name not in excluded and not is_sensitive_field_name(name)
    ]
    return filter_sensitive(visible)


def _fieldsets_payload(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model,
    visible_names: list[str],
) -> list[dict[str, Any]]:
    """Honour ``ModelAdmin.get_fieldsets`` (with a flat fallback).

    Fieldset entries that the admin lists but the visibility filter
    drops are silently removed from the group. An empty result is
    returned as the single "default" group so the SPA always has at
    least one section to render.
    """
    try:
        raw = model_admin.get_fieldsets(request, obj) or ()
    except Exception:
        raw = ()
    if not raw:
        return [{"title": None, "fields": visible_names}]

    visible_set = set(visible_names)
    payload: list[dict[str, Any]] = []
    for title, opts in raw:
        fields = [
            sub
            for entry in opts.get("fields", ())
            for sub in (entry if isinstance(entry, list | tuple) else (entry,))
            if sub in visible_set
        ]
        if fields:
            payload.append({"title": title, "fields": fields})
    return payload or [{"title": None, "fields": visible_names}]


def _fields_payload(
    model: type[Model],
    model_admin: ModelAdmin,
    obj: Model,
    request: HttpRequest,
    visible_names: list[str],
) -> dict[str, dict[str, Any]]:
    """Build the per-field descriptor mapping (contract §4 ``fields``)."""
    readonly = set(model_admin.get_readonly_fields(request, obj) or ())
    form = model_admin.get_form(request, obj=obj)(instance=obj)

    out: dict[str, dict[str, Any]] = {}
    for name in visible_names:
        out[name] = _descriptor_for(
            model=model,
            model_admin=model_admin,
            obj=obj,
            name=name,
            form=form,
            is_readonly=name in readonly,
        )
    return out


def _descriptor_for(
    *,
    model: type[Model],
    model_admin: ModelAdmin,
    obj: Model,
    name: str,
    form: Any,
    is_readonly: bool,
) -> dict[str, Any]:
    """Per-field descriptor for one ``visible_names`` entry."""
    model_field = safe_get_field(model, name)
    if model_field is None:
        return _readonly_callable_descriptor(model_admin, model, obj, name)

    if isinstance(model_field, ForeignKey):
        value: Any = serialize_fk_value(getattr(obj, name, None))
    elif isinstance(model_field, ManyToManyField):
        # M2M (Issue #55): serialise as a list of ``{id, label}``
        # envelopes. The related manager is iterable on a saved row;
        # unsaved rows (e.g. during ``obj=None`` create) have no
        # related set, so default to an empty list.
        try:
            related = list(getattr(obj, name).all())
        except (ValueError, AttributeError):
            related = []
        value = [serialize_fk_value(r) for r in related]
    elif isinstance(model_field, FileField):
        # FileField / ImageField (Issue #57): serialise as a
        # ``{name, url, size}`` envelope. ``None`` when the field is
        # empty. ``url`` defers to the consumer's storage backend so
        # signed-URL backends (S3, GCS) work without package
        # changes; ``size`` is best-effort (some storage backends
        # don't expose it cheaply, so we swallow exceptions).
        value = _serialize_file_value(getattr(obj, name, None))
    else:
        # Forward the model_field so consumer-registered custom
        # serializers (see #60 / ``register_field_type``) take
        # precedence over the default Python-type dispatch.
        value = serialize_value(getattr(obj, name, None), field=model_field)

    form_field = form.fields.get(name)
    required = bool(form_field.required) if form_field is not None else False
    help_text = getattr(model_field, "help_text", "") or (
        form_field.help_text if form_field is not None else ""
    )

    return field_metadata(
        model_field,
        label=_field_label(model_admin, model, name),
        required=required,
        readonly=is_readonly,
        help_text=str(help_text),
        value=value,
    )


def _readonly_callable_descriptor(
    model_admin: ModelAdmin,
    model: type[Model],
    obj: Model,
    name: str,
) -> dict[str, Any]:
    """Descriptor for a readonly callable / method (no underlying field).

    ``ModelAdmin.get_fields`` may include method names or
    ``@admin.display`` callables; those have no model field, so they
    are surfaced as ``type=unsupported`` and ``readonly=True``.
    """
    value = getattr(obj, name, None)
    if callable(value):
        try:
            value = value()
        except Exception:
            value = None
    return {
        "type": "unsupported",
        "label": _field_label(model_admin, model, name),
        "required": False,
        "readonly": True,
        "help_text": "",
        "value": serialize_value(value),
    }


# --------------------------------------------------------------------------- #
# Internals                                                                   #
# --------------------------------------------------------------------------- #
def _serialize_file_value(value: Any) -> dict[str, Any] | None:
    """Serialize a ``FileField``/``ImageField`` value as ``{name, url, size}``.

    Returns ``None`` for empty fields. ``url`` defers to the
    consumer's storage backend (``value.url``) so signed-URL
    backends (S3, GCS, custom) work without package changes —
    we never construct a URL ourselves. ``size`` is best-effort:
    some backends don't expose it cheaply (a HEAD request to S3),
    so we swallow exceptions and return ``None`` for size when
    unavailable.
    """
    if not value:
        return None
    name = getattr(value, "name", "") or ""
    if not name:
        return None
    try:
        url = value.url
    except Exception:
        url = None
    try:
        size = value.size
    except Exception:
        size = None
    return {"name": name, "url": url, "size": size}


def _field_label(model_admin: ModelAdmin, model: type[Model], name: str) -> str:
    """Human-readable label for a field (Django's own helper, with fallback)."""
    try:
        return str(label_for_field(name, model, model_admin))
    except Exception:
        return name
