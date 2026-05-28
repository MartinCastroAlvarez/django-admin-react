"""Object-level change-page actions (Issue #236).

Django's *built-in* admin has no per-object change-page action buttons;
the popular `django-object-actions
<https://github.com/crccheck/django-object-actions>`_ library adds them
via ``ModelAdmin.change_actions`` / ``get_change_actions(request, context,
object_id)``. The library stores callables resolved *by name* and binds
each as a method on the admin instance, so ``getattr(model_admin, name)``
returns the bound callable; it is invoked as ``method(request, obj)`` and
may return ``None`` or an ``HttpResponse``.

This module duck-types that contract so the SPA can surface and run those
actions **when they exist** — without taking a hard dependency on
``django-object-actions``. A plain-Django admin (no
``get_change_actions`` / ``change_actions``) yields the empty list, so the
detail payload simply omits the ``object_actions`` key (a graceful no-op).

Security posture (`SECURITY.md` §3):

- The set of *permitted* actions is resolved through the admin's own
  ``get_change_actions(request, {}, str(obj.pk))`` when available — which
  is exactly how django-object-actions filters by the action's declared
  permission (``_get_permissions_for_action``). The action-run view never
  trusts the URL ``name`` until it appears in that permitted set.
- We never import or assume ``django-object-actions``; everything is
  attribute duck-typing guarded so a misbehaving admin can't 500 the
  endpoint.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import ModelAdmin
from django.http import HttpRequest
from django.utils.text import capfirst


def permitted_action_names(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Any,
) -> list[str] | None:
    """Return the object-action names this request may run, or ``None``.

    Resolution order mirrors django-object-actions:

    1. ``get_change_actions(request, context, object_id)`` — the
       permission-aware hook. When present we call it with an empty
       context and the object's pk; the library returns only the action
       names the user is allowed to run (it applies each action's declared
       permission internally). This is the authoritative, permission-gated
       list.
    2. ``change_actions`` — a plain attribute (list/tuple of names) when
       the admin defines the actions but not the filtering hook. Without
       a permission hook we surface the declared names as-is; the
       action-run view still gates the *object* by ``has_change_permission``
       (object actions are change-shaped).

    Returns ``None`` when the admin exposes neither — the caller then
    omits ``object_actions`` entirely (no-op for a plain-Django admin).
    A list (possibly empty) means the admin opts in.
    """
    hook = getattr(model_admin, "get_change_actions", None)
    if callable(hook):
        try:
            names = hook(request, {}, str(obj.pk) if obj is not None else None)
        except Exception:
            # A consumer hook that raises must not 500 the detail view —
            # degrade to "no actions" rather than leaking the failure.
            return []
        return [str(n) for n in (names or ())]

    declared = getattr(model_admin, "change_actions", None)
    if declared is not None:
        return [str(n) for n in (declared or ())]

    return None


def resolve_action_callable(model_admin: ModelAdmin, name: str) -> Any | None:
    """Resolve one object-action name to its bound callable, or ``None``.

    django-object-actions binds each action as a method on the admin
    instance (whether it was declared as a method name on the admin or as
    a key in ``change_actions``), so ``getattr(model_admin, name)`` is the
    single resolution path. Never trust ``name`` as an arbitrary attribute
    lookup: the caller must first confirm ``name`` is in
    :func:`permitted_action_names`, so we only reach a vetted attribute
    here.
    """
    candidate = getattr(model_admin, name, None)
    return candidate if callable(candidate) else None


def object_actions_payload(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Any,
) -> list[dict[str, str]] | None:
    """Build the detail payload's ``object_actions`` block, or ``None``.

    Each entry is ``{name, label, description}``:

    - ``label`` — the action method's ``label`` attribute if set, else a
      humanized form of the name (``do_thing`` → ``Do thing``), matching
      django-object-actions' own ``capfirst(name.replace("_", " "))``.
    - ``description`` — the method's ``short_description`` if set, else the
      first line of its ``__doc__``; omitted when neither is present.

    Only *permitted* actions (see :func:`permitted_action_names`) are
    included. Returns ``None`` when the admin doesn't expose object
    actions at all, so the caller can drop the key from the response.
    """
    names = permitted_action_names(model_admin, request, obj)
    if names is None:
        return None

    out: list[dict[str, str]] = []
    for name in names:
        callable_ = resolve_action_callable(model_admin, name)
        if callable_ is None:
            # Declared but unresolvable (e.g. a stale name) — skip rather
            # than surfacing a button that the run endpoint would reject.
            continue
        entry: dict[str, str] = {
            "name": name,
            "label": _action_label(callable_, name),
        }
        description = _action_description(callable_)
        if description:
            entry["description"] = description
        out.append(entry)
    return out


def _action_label(action_callable: Any, name: str) -> str:
    """Human-readable button label for an object action."""
    label = getattr(action_callable, "label", None)
    if label:
        return str(label)
    return str(capfirst(name.replace("_", " ")))


def _action_description(action_callable: Any) -> str:
    """Help text for an object action: ``short_description`` or docstring."""
    short = getattr(action_callable, "short_description", None)
    if short:
        return str(short)
    doc = getattr(action_callable, "__doc__", None)
    if doc:
        first_line = doc.strip().splitlines()[0].strip() if doc.strip() else ""
        if first_line:
            return first_line
    return ""
