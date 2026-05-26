"""Inline formset writes (Issue #54, write half).

Read half (``inlines.py``) surfaces each ``InlineModelAdmin`` + its
existing rows in the detail response. This module accepts the SPA's
inline edits on create / update and round-trips them through Django's
**own** inline formset machinery — preserving every ``clean()`` hook,
``save()`` override, and signal the consumer wired up. We never
``setattr`` child rows by hand (rule 3 / 6 / B-3).

Wire shape (the ``"inlines"`` key on a create/update body)::

    {
      "<inline_name>": [
        {"id": 7, "text": "edited"},     # change an existing child
        {"text": "brand new"},            # add a child (no id)
        {"id": 9, "DELETE": true}         # delete an existing child
      ]
    }

``<inline_name>`` is the same ``name`` the read descriptor emits
(``inlines.py::_spec_for_inline``). Rows carry only the inline's
writable fields plus an optional ``id`` and an optional ``DELETE``.

Security properties (each load-bearing, covered by
``tests/test_inline_writes.py``):

- **Per-operation permission gating.** A row that adds a child requires
  ``InlineModelAdmin.has_add_permission(request, parent)``; a row that
  changes one requires ``has_change_permission``; a ``DELETE`` row
  requires ``has_delete_permission``. A payload that attempts an
  operation the inline forbids is rejected (the whole request 403s)
  before any formset is saved.
- **No cross-parent reparenting.** Every submitted ``id`` must already
  belong to *this* parent's child queryset
  (``inline.get_queryset(request)`` filtered to the parent). An ``id``
  belonging to a different parent's child is rejected — the SPA can
  never re-parent or edit a sibling-tree row by guessing a pk.
- **Validation is Django's.** Each formset runs ``is_valid()``; on
  failure the structured errors propagate and the caller rolls the
  whole transaction back (parent + all inlines are atomic).
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import InlineModelAdmin
from django.contrib.admin.options import ModelAdmin
from django.db.models import ForeignKey
from django.db.models import Model
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import QueryDict

from django_admin_react.api.inlines import _resolve_fk_name


class InlinePermissionDenied(Exception):
    """Raised when the payload attempts an inline op the user can't do.

    The view translates this into a 403 (the same posture as a
    top-level permission failure) — the request is refused before any
    formset saves, so a partial write can never land.
    """


def _inline_name(inline: InlineModelAdmin, parent: Model) -> str | None:
    """Recompute the read descriptor's ``name`` for an inline.

    Must match ``inlines.py::_spec_for_inline`` exactly so the SPA can
    round-trip the same key it received on read.
    """
    fk_name = _resolve_fk_name(inline, parent)
    if fk_name is None:
        return None
    child_model = inline.model
    return fk_name + "_set" if not hasattr(child_model, fk_name + "_set") else fk_name


def _inline_by_name(
    model_admin: ModelAdmin, parent: Model, request: HttpRequest
) -> dict[str, InlineModelAdmin]:
    """Map each inline's wire ``name`` to its instance."""
    out: dict[str, InlineModelAdmin] = {}
    try:
        instances = list(model_admin.get_inline_instances(request, obj=parent) or ())
    except Exception:  # pragma: no cover — admin author error
        return out
    for inline in instances:
        name = _inline_name(inline, parent)
        if name is not None:
            out[name] = inline
    return out


def _parent_child_pks(inline: InlineModelAdmin, parent: Model, request: HttpRequest) -> set[Any]:
    """The pks of children that already belong to ``parent``.

    Sourced from ``inline.get_queryset(request)`` (never
    ``Model.objects.all()`` — rule 10) filtered to the parent via the
    resolved FK, so the cross-parent guard only admits rows the parent
    actually owns.
    """
    fk_name = _resolve_fk_name(inline, parent)
    if fk_name is None:
        return set()
    try:
        qs = inline.get_queryset(request).filter(**{fk_name: parent})
        return set(qs.values_list("pk", flat=True))
    except Exception:  # pragma: no cover — defensive
        return set()


def _gate_and_validate_row(
    row: dict[str, Any],
    inline: InlineModelAdmin,
    parent: Model,
    request: HttpRequest,
    owned_pks: set[Any],
) -> None:
    """Permission + cross-parent gate for one inline row.

    Raises :class:`InlinePermissionDenied` if the row attempts an op
    the inline forbids, or references a child the parent doesn't own.
    """
    raw_id = row.get("id")
    is_delete = bool(row.get("DELETE"))

    if raw_id is not None:
        # Cross-parent guard: the id must already be one of this
        # parent's children. Comparison is string-normalised so a
        # JSON int/str id both match the DB pk.
        if not any(str(raw_id) == str(pk) for pk in owned_pks):
            raise InlinePermissionDenied(f"inline row id {raw_id!r} does not belong to this parent")
        if is_delete:
            if not inline.has_delete_permission(request, parent):
                raise InlinePermissionDenied("inline delete not permitted")
        elif not inline.has_change_permission(request, parent):
            raise InlinePermissionDenied("inline change not permitted")
    else:
        if is_delete:
            # A new row marked for deletion is a no-op the SPA should
            # never send; treat as a malformed add attempt.
            raise InlinePermissionDenied("cannot delete an inline row without an id")
        if not inline.has_add_permission(request, parent):
            raise InlinePermissionDenied("inline add not permitted")


def _formset_querydict(prefix: str, rows: list[dict[str, Any]]) -> QueryDict:
    """Translate the clean JSON rows into Django formset POST data.

    Existing rows (those carrying an ``id``) are ordered **first** and
    counted as ``INITIAL_FORMS`` so Django's ``BaseModelFormSet`` maps
    each initial form to its existing instance by the submitted ``id``;
    new rows follow as extra forms. Field values are stringified the
    way an HTML form post would carry them.
    """
    existing = [r for r in rows if r.get("id") is not None]
    new = [r for r in rows if r.get("id") is None]
    ordered = existing + new

    data = QueryDict(mutable=True)
    data[f"{prefix}-TOTAL_FORMS"] = str(len(ordered))
    data[f"{prefix}-INITIAL_FORMS"] = str(len(existing))
    data[f"{prefix}-MIN_NUM_FORMS"] = "0"
    data[f"{prefix}-MAX_NUM_FORMS"] = "1000"

    for i, row in enumerate(ordered):
        for key, value in row.items():
            if key == "id":
                data[f"{prefix}-{i}-id"] = str(value)
            elif key == "DELETE":
                if value:
                    data[f"{prefix}-{i}-DELETE"] = "on"
            else:
                data[f"{prefix}-{i}-{key}"] = "" if value is None else str(value)
    return data


def build_inline_formsets(
    model_admin: ModelAdmin,
    parent: Model,
    request: HttpRequest,
    inlines_payload: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    """Build + validate inline formsets from the payload.

    Returns ``(formsets, errors)``. When ``errors`` is non-empty the
    caller must **not** save anything and should roll back. When it is
    empty, ``formsets`` is the list of validated formsets to save
    inside the parent's transaction.

    Raises :class:`InlinePermissionDenied` (→ 403) if any row attempts
    a forbidden op or references a non-owned child.
    """
    name_map = _inline_by_name(model_admin, parent, request)
    formsets: list[Any] = []
    errors: dict[str, Any] = {}

    for name, rows in inlines_payload.items():
        inline = name_map.get(name)
        if inline is None:
            errors[name] = ["Unknown inline."]
            continue
        if not isinstance(rows, list):
            errors[name] = ["Inline payload must be a list of rows."]
            continue

        owned_pks = _parent_child_pks(inline, parent, request)
        for row in rows:
            if not isinstance(row, dict):
                errors[name] = ["Each inline row must be an object."]
                break
            _gate_and_validate_row(row, inline, parent, request, owned_pks)
        if name in errors:
            continue

        formset_class = inline.get_formset(request, parent)
        prefix = formset_class.get_default_prefix()
        data = _formset_querydict(prefix, rows)
        formset = formset_class(data=data, instance=parent, prefix=prefix)
        if not formset.is_valid():
            errors[name] = formset.errors
            continue
        formsets.append(formset)

    return formsets, errors


def inline_validation_failed(inline_errors: dict[str, Any]) -> HttpResponse:
    """Return a 400 envelope for inline formset validation failures.

    Mirrors ``writes.validation_failed`` but nests the per-inline
    errors under ``error.details.inlines`` (contract §5.6), since the
    shape is per-inline-per-row rather than the flat field map the
    top-level form uses.
    """
    body = {
        "error": {
            "code": "validation_failed",
            "message": "One or more inline rows are invalid.",
            "details": {"inlines": inline_errors},
        }
    }
    response = JsonResponse(body, status=400)
    response["Cache-Control"] = "no-store"
    return response


def save_inline_formsets(
    formsets: list[Any],
    model_admin: ModelAdmin,
    request: HttpRequest,
    change: bool,
) -> None:
    """Persist validated formsets through Django's ``save_formset``.

    Delegates to ``ModelAdmin.save_formset`` (the same hook the HTML
    admin calls) so consumer overrides + signals fire. Must be called
    inside the caller's ``transaction.atomic()`` block, after the
    parent is saved. ``change`` is ``False`` on the add view and
    ``True`` on the change view (matches Django's
    ``save_related`` call).
    """
    for formset in formsets:
        model_admin.save_formset(request, form=None, formset=formset, change=change)


def has_inline_field(field_model: type[Model], fk_name: str) -> bool:  # pragma: no cover
    """Best-effort check that ``fk_name`` is a real FK on the child."""
    try:
        return isinstance(field_model._meta.get_field(fk_name), ForeignKey)
    except Exception:
        return False
