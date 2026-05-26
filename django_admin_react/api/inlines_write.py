"""Inline formset write path (Issue #54, write half — PR 2 of the split).

Wire contract: ``docs/api-contract.md`` §5.4 (inline writes).

The read half (#109, ``api/inlines.py``) surfaces each declared
``InlineModelAdmin`` and its existing rows on the detail response. This
module is the **write** counterpart: it takes the ``inlines`` block of a
PATCH/POST payload and round-trips it through Django's own inline
formset machinery, exactly the way ``ModelAdmin.changeform_view`` does.

Why a formset and not a per-row ``save()`` loop (Architect rule 3):
iterating rows and calling ``child.save()`` each would bypass the
formset's ``clean()`` / ``clean_m2m()`` and the inline's
``save_formset`` hook — losing the consumer's cross-row validation and
any signals they rely on. We build the real formset, validate it as a
unit, and call ``model_admin.save_formset(...)``.

Security model (Architect contract + `SECURITY.md` §3):

- **Rule 1** — everything reuses ``InlineModelAdmin``; no parallel
  inline-config or write path.
- **Rule 3** — rows round-trip through
  ``inline.get_formset(request, obj=parent)`` + ``formset.save()``.
- **Per-row permission gates** — each row's *state* is gated by the
  inline's own permission method against the **parent** object:
  - a new row (``pk`` is null) requires ``has_add_permission``;
  - an edited existing row requires ``has_change_permission``;
  - a ``DELETE`` row requires ``has_delete_permission``.
  A single failing gate makes the **whole** PATCH roll back — the
  caller wraps this in ``transaction.atomic()`` and treats a returned
  ``PermissionError`` as a 403 that reverts the parent write too.
- **Deny-by-default lookup** — an ``inlines`` key that doesn't match a
  declared inline on this parent is rejected (400), never silently
  ignored (no mass-assignment via an unrecognised prefix).

Out of scope (firm — documented in the PR and the contract):

- Nested inlines (inline-of-inline).
- ``GenericInlineModelAdmin`` (contenttypes).
- M2M-through inlines with extra fields (surfaced as ``unsupported`` by
  the read half; writes are refused here for the same reason).
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import InlineModelAdmin
from django.contrib.admin.options import ModelAdmin
from django.db.models import Model
from django.forms.models import BaseModelFormSet
from django.http import HttpRequest

from django_admin_react.api.inlines import _get_inline_instances
from django_admin_react.api.inlines import _resolve_fk_name


class InlinePermissionDenied(Exception):
    """A per-row state was not permitted for the requesting user.

    Raised (not returned) so the caller's ``transaction.atomic()`` block
    unwinds the parent write as well — a forbidden inline row must never
    leave a half-applied PATCH behind. The caller converts this to a 403.
    """

    def __init__(self, inline_name: str, state: str) -> None:
        super().__init__(f"inline {inline_name!r}: {state} not permitted")
        self.inline_name = inline_name
        self.state = state


def _inline_name(inline: InlineModelAdmin, parent: Model) -> str:
    """The identifier the read half emits for this inline.

    Must match ``inlines.py``'s ``_spec_for_inline`` so the SPA can echo
    the same key back on write. Kept in one place would be ideal; this
    mirrors the read-half computation deliberately and the
    ``test_inline_write_name_matches_read`` regression pins them
    together.
    """
    child_model = inline.model
    fk_name = _resolve_fk_name(inline, parent)
    if fk_name is None:
        return child_model._meta.model_name
    if hasattr(child_model, fk_name + "_set"):
        return fk_name
    return fk_name + "_set"


def _formset_data_for(prefix: str, items: list[dict[str, Any]]) -> dict[str, str]:
    """Translate JSON inline rows into Django formset POST-style data.

    Django's ``BaseModelFormSet`` treats the first ``INITIAL_FORMS``
    forms as *existing* (keyed by their ``id`` field) and the rest as
    *new*. So the items are ordered **existing-first** by the caller and
    ``INITIAL_FORMS`` is set to the count of rows carrying a ``pk``.

    Scalar values are stringified (the form fields coerce them back);
    ``None`` becomes the empty string the way an empty HTML input would.
    A truthy ``DELETE`` flag sets the formset's per-form ``DELETE``
    checkbox.
    """
    initial = sum(1 for it in items if it.get("pk") is not None)
    data: dict[str, str] = {
        f"{prefix}-TOTAL_FORMS": str(len(items)),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for i, item in enumerate(items):
        pk = item.get("pk")
        if pk is not None:
            data[f"{prefix}-{i}-id"] = str(pk)
        for fname, fval in (item.get("fields") or {}).items():
            data[f"{prefix}-{i}-{fname}"] = "" if fval is None else str(fval)
        if item.get("DELETE"):
            data[f"{prefix}-{i}-DELETE"] = "on"
    return data


def _ordered_items(raw_items: Any) -> list[dict[str, Any]]:
    """Validate + order the incoming row list: existing (``pk``) first.

    Raises ``ValueError`` on a malformed payload (not a list, or a row
    that isn't an object) so the caller returns a 400 rather than a 500.
    """
    if not isinstance(raw_items, list):
        raise ValueError("inline 'items' must be a list")
    items: list[dict[str, Any]] = []
    for row in raw_items:
        if not isinstance(row, dict):
            raise ValueError("each inline row must be an object")
        items.append(row)
    existing = [it for it in items if it.get("pk") is not None]
    new = [it for it in items if it.get("pk") is None]
    return existing + new


def _gate_row_states(
    inline: InlineModelAdmin,
    parent: Model,
    request: HttpRequest,
    items: list[dict[str, Any]],
    name: str,
) -> None:
    """Raise ``InlinePermissionDenied`` if any row state isn't allowed.

    Gates **before** the formset saves so a forbidden state never
    partially persists. Checks the inline's own permission methods
    against the parent object (not the parent admin's) per the Architect
    contract.
    """
    wants_add = any(it.get("pk") is None and not it.get("DELETE") for it in items)
    wants_change = any(it.get("pk") is not None and not it.get("DELETE") for it in items)
    wants_delete = any(it.get("DELETE") for it in items)

    if wants_add and not inline.has_add_permission(request, parent):
        raise InlinePermissionDenied(name, "add")
    if wants_change and not inline.has_change_permission(request, parent):
        raise InlinePermissionDenied(name, "change")
    if wants_delete and not inline.has_delete_permission(request, parent):
        raise InlinePermissionDenied(name, "delete")


def apply_inline_writes(
    model_admin: ModelAdmin,
    request: HttpRequest,
    parent: Model,
    parent_form: Any,
    inlines_payload: dict[str, Any],
) -> dict[str, dict[str, Any]] | None:
    """Validate + save every inline formset in ``inlines_payload``.

    Returns ``None`` on success. On formset validation failure returns
    an errors dict keyed by inline name (so the caller returns 400 and
    rolls back). Raises :class:`InlinePermissionDenied` on a forbidden
    row state (caller → 403 + rollback). Raises ``ValueError`` on a
    malformed payload shape (caller → 400).

    Must be called **inside** the caller's ``transaction.atomic()``
    block, after the parent form has saved, so a failure here reverts
    the parent write too.
    """
    if not isinstance(inlines_payload, dict):
        raise ValueError("'inlines' must be an object keyed by inline name")

    # Map declared inlines by the read-half name so an unknown key is a
    # 400 (deny-by-default) rather than a silently-ignored payload.
    inlines = _get_inline_instances(model_admin, parent, request)
    by_name: dict[str, InlineModelAdmin] = {
        _inline_name(inline, parent): inline for inline in inlines
    }
    unknown = set(inlines_payload) - set(by_name)
    if unknown:
        raise ValueError("unknown inline(s): " + ", ".join(sorted(unknown)))

    errors: dict[str, dict[str, Any]] = {}

    for name, block in inlines_payload.items():
        inline = by_name[name]
        if not isinstance(block, dict):
            raise ValueError(f"inline {name!r} must be an object with 'items'")
        items = _ordered_items(block.get("items", []))
        if not items:
            continue

        # Per-row permission gate BEFORE building/saving the formset.
        _gate_row_states(inline, parent, request, items, name)

        formset_class = inline.get_formset(request, obj=parent)
        prefix = formset_class.get_default_prefix()
        formset: BaseModelFormSet = formset_class(
            data=_formset_data_for(prefix, items),
            instance=parent,
            prefix=prefix,
        )
        if not formset.is_valid():
            errors[name] = {"formset": formset.errors, "non_form": list(formset.non_form_errors())}
            continue

        # Round-trip through the admin's save hook (rule 3) — never a
        # per-row save loop. ``save_formset`` runs the consumer's
        # ``save_formset`` override + ``save_m2m`` for the children.
        model_admin.save_formset(request, parent_form, formset, change=True)

    return errors or None
