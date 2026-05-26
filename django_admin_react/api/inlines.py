"""``ModelAdmin.inlines`` surfacing on the detail endpoint (Issue #54).

Wire contract: ``docs/api-contract.md`` §4.2.

For each ``InlineModelAdmin`` declared on the parent ``ModelAdmin``,
the detail response includes a metadata block plus the existing
child rows. Write support (formset round-trip) is tracked as a
follow-up — this PR closes the *read* half of #54 so the SPA can
render inlines for view-only flows immediately.

Hard rules (`SECURITY.md` §3):

- Rule 5:  Each inline's child rows are gated by the *child's*
  ``has_view_permission`` — the parent's view permission is not
  enough; an inline pointing at a model the user can't see is
  surfaced with an empty ``rows`` list and ``can_view: false``.
- Rule 10: Child querysets start at the inline's ``get_queryset``
  (which inherits from ``ModelAdmin.get_queryset``).
- Rule 12: Sensitive-name denylist applies per-field on inline rows
  just like the top-level detail.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import InlineModelAdmin
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.utils import label_for_field
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model
from django.http import HttpRequest

from django_admin_react.api.serializers import field_type_for
from django_admin_react.api.serializers import filter_sensitive
from django_admin_react.api.serializers import is_sensitive_field_name
from django_admin_react.api.serializers import label_for
from django_admin_react.api.serializers import safe_get_field
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value


def inlines_payload(
    model_admin: ModelAdmin, parent: Model, request: HttpRequest
) -> list[dict[str, Any]]:
    """Build the ``inlines`` block of the detail response.

    Empty list when no ``inlines`` declared. Each entry::

        {
          "name": "comments",
          "label": "Comments",
          "kind": "tabular" | "stacked",
          "fk_name": "post",
          "child": {"app_label": "blog", "model_name": "comment"},
          "extra": 1,
          "min_num": 0,
          "max_num": null,
          "can_delete": true,
          "can_view": true,
          "can_add": true,
          "can_change": true,
          "fields": [
            {"name": "text", "label": "Text", "type": "string",
             "required": true, "readonly": false}
          ],
          "rows": [
            {"pk": 7, "label": "Comment object (7)",
             "fields": {"text": "Hi!"}}
          ]
        }
    """
    out: list[dict[str, Any]] = []
    inline_instances = _get_inline_instances(model_admin, parent, request)
    for inline in inline_instances:
        entry = _spec_for_inline(inline, parent, request)
        if entry is not None:
            out.append(entry)
    return out


def _get_inline_instances(
    model_admin: ModelAdmin, parent: Model, request: HttpRequest
) -> list[InlineModelAdmin]:
    """Resolve the parent admin's inline instances.

    Defensive: a typo'd ``inlines`` entry or an inline whose
    ``InlineModelAdmin.get_queryset`` raises must not break the
    parent detail view. Errors are swallowed and the offending
    inline is skipped.
    """
    try:
        return list(model_admin.get_inline_instances(request, obj=parent) or ())
    except Exception:  # pragma: no cover — admin author error
        return []


def _spec_for_inline(
    inline: InlineModelAdmin, parent: Model, request: HttpRequest
) -> dict[str, Any] | None:
    """Build one inline's metadata + rows payload.

    Returns ``None`` if the inline can't be resolved cleanly (e.g.
    missing FK back to the parent) so the parent detail keeps
    rendering. The omission is announced via the missing entry
    rather than a 500 — the SPA still sees the other inlines.
    """
    child_model = inline.model
    meta = child_model._meta

    fk_name = _resolve_fk_name(inline, parent)
    if fk_name is None:
        return None

    # Per-inline permissions, gated by the child's ModelAdmin.
    can_view = bool(inline.has_view_permission(request, parent))
    can_add = bool(inline.has_add_permission(request, parent))
    can_change = bool(inline.has_change_permission(request, parent))
    can_delete = bool(inline.has_delete_permission(request, parent))

    kind = "tabular" if "Tabular" in type(inline).__name__ else "stacked"

    visible_fields = _visible_inline_fields(inline, parent, request)
    fields_meta = _fields_meta(inline, child_model, visible_fields, request)

    rows: list[dict[str, Any]] = []
    if can_view:
        rows = _rows_for_inline(inline, parent, fk_name, visible_fields, request)

    return {
        "name": fk_name + "_set" if not hasattr(child_model, fk_name + "_set") else fk_name,
        "label": str(meta.verbose_name_plural),
        "kind": kind,
        "fk_name": fk_name,
        "child": {"app_label": meta.app_label, "model_name": meta.model_name},
        "extra": int(getattr(inline, "extra", 0)),
        "min_num": getattr(inline, "min_num", None),
        "max_num": getattr(inline, "max_num", None),
        "can_view": can_view,
        "can_add": can_add,
        "can_change": can_change,
        "can_delete": can_delete,
        "fields": fields_meta,
        "rows": rows,
    }


def _resolve_fk_name(inline: InlineModelAdmin, parent: Model) -> str | None:
    """Find the FK on the child that points back at the parent.

    If the inline declares ``fk_name`` use it; otherwise scan the
    child's FK fields for one whose related model is the parent's
    class (or a superclass).
    """
    declared = getattr(inline, "fk_name", None)
    if declared:
        return declared
    parent_class = type(parent)
    for field in inline.model._meta.get_fields():
        if isinstance(field, ForeignKey):
            related = field.related_model
            if related is parent_class or (
                related is not None
                and not isinstance(related, str)
                and issubclass(parent_class, related)
            ):
                return field.name
    return None


def _visible_inline_fields(
    inline: InlineModelAdmin, parent: Model, request: HttpRequest
) -> list[str]:
    """Field names the inline surfaces (read).

    Mirrors the top-level detail view's visibility rules:
    ``get_fields`` minus ``get_exclude`` minus sensitive-name
    denylist. The implicit FK back to the parent is excluded — the
    SPA doesn't need it (it's implied by the inline's nesting).
    """
    declared = list(inline.get_fields(request, parent) or ())
    excluded = set(inline.get_exclude(request, parent) or ())
    fk_back = _resolve_fk_name(inline, parent)
    visible = [
        name
        for name in declared
        if isinstance(name, str)
        and name not in excluded
        and name != fk_back
        and not is_sensitive_field_name(name)
    ]
    return filter_sensitive(visible)


def _fields_meta(
    inline: InlineModelAdmin,
    child_model: type[Model],
    visible_fields: list[str],
    request: HttpRequest,
) -> list[dict[str, Any]]:
    """Per-field metadata for the inline header.

    Carries ``type`` + ``required`` (in addition to ``name`` / ``label``
    / ``readonly``) so the SPA can render a *typed* input per inline
    field in edit mode — the prerequisite for inline editing (#54
    write-half UI). ``type`` reuses the same closed vocabulary
    (``field_type_for``) the top-level detail descriptor uses, so the
    frontend can route inline fields through the same ``FieldInput``
    component. Additive — existing read-only consumers ignore the new
    keys.
    """
    readonly = set(inline.get_readonly_fields(request, None) or ())
    out: list[dict[str, Any]] = []
    for name in visible_fields:
        label: Any
        try:
            label = label_for_field(name, child_model, inline)
        except Exception:  # pragma: no cover
            label = name
        model_field = safe_get_field(child_model, name)
        field_type = field_type_for(model_field) if model_field is not None else "unsupported"
        # ``required`` mirrors the form layer: a field is required when
        # it is not ``blank``. ``safe_get_field`` returning ``None`` (a
        # method-only ``list_display`` entry) → not required / unsupported.
        required = bool(model_field is not None and not getattr(model_field, "blank", True))
        out.append(
            {
                "name": name,
                "label": str(label),
                "readonly": name in readonly,
                "type": field_type,
                "required": required,
            }
        )
    return out


def _rows_for_inline(
    inline: InlineModelAdmin,
    parent: Model,
    fk_name: str,
    visible_fields: list[str],
    request: HttpRequest,
) -> list[dict[str, Any]]:
    """Fetch + serialize the child rows attached to ``parent``."""
    try:
        queryset = inline.get_queryset(request).filter(**{fk_name: parent.pk})
    except Exception:  # pragma: no cover
        return []
    rows: list[dict[str, Any]] = []
    for obj in queryset:
        fields_payload: dict[str, Any] = {}
        for name in visible_fields:
            model_field = None
            try:
                model_field = inline.model._meta.get_field(name)
            except Exception:
                model_field = None
            value = getattr(obj, name, None)
            if isinstance(model_field, ForeignKey):
                fields_payload[name] = serialize_fk_value(value)
            elif isinstance(model_field, ManyToManyField):
                try:
                    related = list(value.all()) if value is not None else []
                except Exception:
                    related = []
                fields_payload[name] = [serialize_fk_value(r) for r in related]
            else:
                fields_payload[name] = serialize_value(value, field=model_field)
        rows.append({"pk": obj.pk, "label": label_for(obj), "fields": fields_payload})
    return rows
