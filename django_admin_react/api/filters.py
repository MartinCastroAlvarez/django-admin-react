"""``list_filter`` surfacing for the list endpoint (Issue #56).

Wire contract: ``docs/api-contract.md`` §3.3.

When a ``ModelAdmin`` declares ``list_filter = (...)``, the list
endpoint:

1. Surfaces the filter metadata (`filters: [...]`) so the SPA can
   render the left-sidebar filter strip.
2. Reads per-filter query params and narrows the queryset accordingly.

Supported filter types in v1:

- **`SimpleListFilter` subclass** — the filter's own ``parameter_name``
  + ``lookups(request, model_admin)`` drive the SPA's options;
  ``queryset(request, qs)`` does the narrowing.
- **Boolean field** — three-way: ``true`` / ``false`` / unset.
- **Field with choices** — one option per choice.
- **ForeignKey** — small target tables only (≤ 25 rows per PM ruling).
  The SPA fetches choices via the existing list endpoint when needed.
- **DateField / DateTimeField** — the date_hierarchy strip (Issue #62)
  handles the heavy case; ``list_filter`` on a date field is surfaced
  as ``{type: "date"}`` but defers detailed date-range UX to a follow-up.

Hard rules (`SECURITY.md` §3):

- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)``;
  filters are applied on top, never bypass the admin's gate.
- Rule 12: Unknown filter params are silently ignored. Garbage values
  ("``?status=garbage``") fall through to the admin's own validation —
  if the admin would reject the value, the queryset returns no rows
  (which is the correct posture — a 500 would be wrong).
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin import SimpleListFilter
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.db.models import BooleanField
from django.db.models import DateField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import Model
from django.db.models import QuerySet
from django.http import HttpRequest

from django_admin_react.api.serializers import is_sensitive_field_name

# PM ruling (Q-PM-03): FK filters in v1 surface up to ≤ 25 options
# inline; larger target tables defer to a follow-up that combines
# list_filter with autocomplete (#59). Keep the cap explicit so a
# consumer doesn't accidentally render a 10k-option dropdown.
_FK_FILTER_MAX_OPTIONS = 25


def _entry_spec(entry: Any) -> tuple[str | None, type | None]:
    """Normalize a `list_filter` entry to ``(field_name, filter_cls)``.

    Django accepts entries in three forms:

    - ``"field_name"`` → use the field's default filter.
    - ``("field_name", FilterClass)`` → use the explicit filter class.
    - ``FilterClass`` (a ``SimpleListFilter`` subclass) → no field;
      the filter declares its own ``parameter_name``.
    """
    if isinstance(entry, str):
        return entry, None
    if isinstance(entry, tuple) and len(entry) == 2 and isinstance(entry[0], str):
        return entry[0], entry[1]
    if isinstance(entry, type) and issubclass(entry, SimpleListFilter):
        return None, entry
    return None, None


def _safe_get_field(model: type[Model], name: str):
    """Return ``model._meta.get_field(name)`` or ``None``."""
    try:
        return model._meta.get_field(name)
    except Exception:
        return None


def _spec_for_boolean(field_name: str, field: Any) -> dict[str, Any]:
    return {
        "name": field_name,
        "label": str(getattr(field, "verbose_name", field_name) or field_name).strip(),
        "type": "boolean",
    }


def _spec_for_choices(field_name: str, field: Any) -> dict[str, Any]:
    raw_choices = list(getattr(field, "choices", None) or [])
    return {
        "name": field_name,
        "label": str(getattr(field, "verbose_name", field_name) or field_name).strip(),
        "type": "choice",
        "choices": [{"value": v, "label": str(lbl)} for v, lbl in raw_choices],
    }


def _spec_for_fk(
    field_name: str,
    field: ForeignKey,
    request: HttpRequest,
    admin_site: AdminSite | None = None,
) -> dict[str, Any] | None:
    """Build the metadata block for an FK filter.

    Returns ``None`` (i.e. drop the descriptor) when the related model
    is **not registered** with the admin site — the SPA's FK picker
    would otherwise 404 on the related list endpoint, and the bare
    ``to: {app_label, model_name}`` discloses the existence of an
    unregistered model (see issue #89, defense-in-depth).
    """
    related = field.related_model
    meta = related._meta if related is not None else None
    if related is None or meta is None:
        return None
    # #89: drop the descriptor entirely if the related model isn't in
    # the configured admin site. This keeps the closed-vocabulary
    # posture tight (the SPA only learns about FK filters it can
    # actually populate) and removes one information-disclosure rung.
    if admin_site is not None and related not in admin_site._registry:
        return None
    payload: dict[str, Any] = {
        "name": field_name,
        "label": str(getattr(field, "verbose_name", field_name) or field_name).strip(),
        "type": "foreignkey",
        "to": {"app_label": meta.app_label, "model_name": meta.model_name},
    }
    # Inline up to _FK_FILTER_MAX_OPTIONS choices for tiny tables;
    # larger tables defer to the autocomplete endpoint (#59).
    try:
        count = related._default_manager.count()
    except Exception:
        count = _FK_FILTER_MAX_OPTIONS + 1
    if count <= _FK_FILTER_MAX_OPTIONS:
        from django_admin_react.api.serializers import label_for

        payload["choices"] = [
            {"value": obj.pk, "label": label_for(obj)}
            for obj in related._default_manager.all()[:_FK_FILTER_MAX_OPTIONS]
        ]
    return payload


def _spec_for_date(field_name: str, field: Any) -> dict[str, Any]:
    return {
        "name": field_name,
        "label": str(getattr(field, "verbose_name", field_name) or field_name).strip(),
        "type": "date",
    }


def _spec_for_simple_filter(
    filter_cls: type, model_admin: ModelAdmin, request: HttpRequest
) -> dict[str, Any] | None:
    """Build the metadata block for a ``SimpleListFilter`` subclass."""
    try:
        instance = filter_cls(request, request.GET.copy(), model_admin.model, model_admin)
    except Exception:  # pragma: no cover — admin author error
        return None
    try:
        lookups = list(instance.lookups(request, model_admin) or [])
    except Exception:  # pragma: no cover — admin author error
        lookups = []
    return {
        "name": instance.parameter_name,
        "label": str(getattr(instance, "title", "") or instance.parameter_name),
        "type": "custom",
        "lookups": [{"value": v, "label": str(lbl)} for v, lbl in lookups],
    }


def filters_payload(
    model_admin: ModelAdmin,
    request: HttpRequest,
    admin_site: AdminSite | None = None,
) -> list[dict[str, Any]]:
    """Build the ``filters`` block of the list response.

    Empty list when the admin doesn't declare ``list_filter`` or no
    entry resolves to a supported type. The block is always present
    (empty `[]`) so the SPA can branch on `filters.length` without
    `if "filters" in response`.

    Defense-in-depth (issues #88, #89):

    - Sensitive-name fields (``password``, ``api_key``, …) are
      silently dropped from the descriptor list. Mirrors
      ``filter_sensitive`` posture on the rest of the API and
      protects against admin authors who forget to ``exclude``.
    - FK filters whose target model isn't in the configured admin
      site's registry are silently dropped — no leak of adjacency to
      unregistered models.
    """
    raw = list(model_admin.get_list_filter(request) or ())
    if not raw:
        return []

    model = model_admin.model
    out: list[dict[str, Any]] = []
    for entry in raw:
        field_name, filter_cls = _entry_spec(entry)

        if filter_cls is not None and issubclass(filter_cls, SimpleListFilter):
            spec = _spec_for_simple_filter(filter_cls, model_admin, request)
            if spec is None:
                continue
            # #88: a SimpleListFilter whose ``parameter_name`` matches
            # the sensitive-name denylist is dropped — same posture as
            # field-based filters below. A consumer naming their
            # custom filter ``password_filter`` would otherwise
            # surface ``name: "password_filter"`` on the wire.
            if is_sensitive_field_name(spec.get("name", "")):
                continue
            out.append(spec)
            continue

        if field_name is None:
            continue

        # #88: defense-in-depth — sensitive-named fields are dropped
        # before any other dispatch. Matches the registry endpoint's
        # posture and ``filter_sensitive``'s behavior on the rest of
        # the API.
        if is_sensitive_field_name(field_name):
            continue

        field = _safe_get_field(model, field_name)
        if field is None:
            continue
        if isinstance(field, BooleanField):
            out.append(_spec_for_boolean(field_name, field))
        elif isinstance(field, ForeignKey):
            fk_spec = _spec_for_fk(field_name, field, request, admin_site=admin_site)
            if fk_spec is not None:
                out.append(fk_spec)
        elif getattr(field, "choices", None):
            out.append(_spec_for_choices(field_name, field))
        elif isinstance(field, DateTimeField | DateField):
            out.append(_spec_for_date(field_name, field))
        # Anything else: silently skipped. Unknown filter types are a
        # back-compat surface — adding support in a follow-up never
        # breaks existing responses.
    return out


def apply_filters(queryset: QuerySet, model_admin: ModelAdmin, request: HttpRequest) -> QuerySet:
    """Narrow ``queryset`` by every active ``list_filter`` query param.

    For ``SimpleListFilter`` entries, the filter's own
    ``queryset(request, qs)`` does the narrowing — exactly as the
    legacy admin invokes it.

    For field-based entries, the param name is the field name and the
    value is the raw lookup. Unknown / garbage values fall through to
    Django's ORM — if the value can't be coerced, the queryset
    returns no rows (correct posture; the SPA should rely on the
    metadata to show only valid options).
    """
    raw = list(model_admin.get_list_filter(request) or ())
    if not raw:
        return queryset

    model = model_admin.model
    for entry in raw:
        field_name, filter_cls = _entry_spec(entry)

        if filter_cls is not None and issubclass(filter_cls, SimpleListFilter):
            try:
                instance = filter_cls(request, request.GET.copy(), model_admin.model, model_admin)
            except Exception:  # pragma: no cover
                continue
            try:
                narrowed = instance.queryset(request, queryset)
            except Exception:  # pragma: no cover
                narrowed = None
            if narrowed is not None:
                queryset = narrowed
            continue

        if field_name is None:
            continue
        raw_value = request.GET.get(field_name)
        if raw_value in (None, ""):
            continue

        field = _safe_get_field(model, field_name)
        if field is None:
            continue

        try:
            if isinstance(field, BooleanField):
                if raw_value.lower() in ("true", "1", "yes"):
                    queryset = queryset.filter(**{field_name: True})
                elif raw_value.lower() in ("false", "0", "no"):
                    queryset = queryset.filter(**{field_name: False})
                # "all" / any other → no filter applied
                continue
            if isinstance(field, ForeignKey):
                queryset = queryset.filter(**{f"{field_name}_id": raw_value})
                continue
            if getattr(field, "choices", None):
                queryset = queryset.filter(**{field_name: raw_value})
                continue
            if isinstance(field, DateTimeField | DateField):
                # v1: support an exact-date match. Range UX deferred.
                queryset = queryset.filter(**{field_name: raw_value})
                continue
        except Exception:
            # Garbage value that broke the ORM — narrow to zero
            # rows rather than 500. The SPA sees an empty result set
            # and the metadata block tells it the value was bad.
            return queryset.none()

    return queryset
