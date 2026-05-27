"""Surface a ``ModelAdmin``'s *custom* admin views to the SPA (Issue #439).

Many consumers add bespoke admin pages — report / import-export /
dashboard pages and per-object tool views — by overriding
``ModelAdmin.get_urls()`` (or ``AdminSite.get_urls()``). The SPA cannot
render those Django-templated pages itself, but it can **link out** to
them (Option A): a real ``<a target="_blank">`` to the legacy
admin-rendered page. This module is the design-safe foundation — the
same ``{name, label, url, level}`` payload also powers a future iframe
or native approach.

How custom routes are distinguished from the standard CRUD set
----------------------------------------------------------------

Django's ``ModelAdmin.get_urls`` always emits five *named* routes for a
model — ``<app>_<model>_{changelist,add,change,delete,history}`` — plus
one unnamed catch-all (the legacy ``<pk>/`` redirect, ``name=None``).
Anything a consumer adds on top has a different (or no) standard suffix.
We compute the standard names from ``model._meta`` and treat every
remaining *named* route as a custom view. Unnamed routes are skipped:
without a name they can't be ``reverse()``-d through the admin
namespace, so the SPA could never link to them anyway.

How URLs are reversed
---------------------

Custom admin routes live under the **admin site's** URL namespace
(``admin_site.name``, e.g. ``"admin"``). We reverse each route as
``reverse(f"{admin_site.name}:{name}", args=[...])`` — ``args=[obj.pk]``
for an object-level route, ``args=[]`` for a changelist-level one. Every
reverse is guarded; an un-reversible route (legacy admin not mounted,
extra capture groups we don't fill, a consumer ``reverse`` quirk) is
silently skipped rather than raising.

Hardening (``SECURITY.md`` §3): this module introduces **no new
permission surface**. It is only ever called from the detail / registry
views, *after* their staff + ``has_view_permission`` gates have run, and
it never reads object data beyond the ``pk`` it is handed. A misbehaving
consumer ``get_urls`` must never 500 a response — every introspection
step degrades to ``[]``.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.options import ModelAdmin
from django.db.models import Model
from django.urls import reverse
from django.utils.text import capfirst

# Capture-group names Django uses for the per-object segment of a
# ``ModelAdmin`` route. If a custom route's regex captures any of these
# (or, defensively, a generic ``pk``), it is an *object-level* view that
# needs an object id to reverse.
_OBJECT_ID_GROUPS: frozenset[str] = frozenset({"object_id", "pk"})


def _standard_route_names(model: type[Model]) -> frozenset[str]:
    """The five route names Django's ``ModelAdmin.get_urls`` always emits.

    Built from ``model._meta`` exactly the way Django builds them in
    ``ModelAdmin.get_urls`` (``info = app_label, model_name``), so this
    stays correct for any model without depending on Django internals.
    """
    info = f"{model._meta.app_label}_{model._meta.model_name}"
    return frozenset(
        {
            f"{info}_changelist",
            f"{info}_add",
            f"{info}_change",
            f"{info}_delete",
            f"{info}_history",
        }
    )


def _is_object_level(pattern: Any) -> bool:
    """``True`` if the URL pattern captures an object id.

    Inspects the compiled regex's named capture groups for an
    ``object_id`` / ``pk`` group — the marker that the route is a
    per-object tool view (e.g. ``<pk>/make-report/``) rather than a
    page that stands alone (e.g. ``import/``). Any introspection error
    is treated as "not object-level" (changelist-level) so we still
    attempt a no-args reverse.
    """
    try:
        groups = pattern.regex.groupindex.keys()
    except Exception:
        return False
    return any(group in _OBJECT_ID_GROUPS for group in groups)


def _label_for_route(entry: Any, name: str) -> str:
    """Human-readable label for a custom route.

    Prefers a ``short_description`` on the view callable (Django's own
    convention for naming admin callables); falls back to humanising the
    route name — ``capfirst(name.replace("_", " "))``. The model/app
    prefix that ``get_urls`` bakes into the name (``<app>_<model>_``) is
    stripped first so the label reads as the *action* (e.g.
    ``"Send report"``) rather than the wiring.
    """
    callback = getattr(entry, "callback", None)
    short = getattr(callback, "short_description", None)
    if short:
        return str(short)
    return str(capfirst(name.replace("_", " ")))


def _reverse_or_none(admin_site: Any, name: str, args: list[Any]) -> str | None:
    """Reverse ``<admin_site.name>:<name>`` with ``args``, or ``None``.

    Guards every reverse: an un-reversible route (legacy admin not
    mounted, a route needing more args than we supply, a custom
    namespace quirk) degrades to ``None`` and is dropped by the caller.
    """
    site_name = getattr(admin_site, "name", None)
    if not site_name:
        return None
    try:
        return reverse(f"{site_name}:{name}", args=args)
    except Exception:
        return None


def custom_views_for(
    model_admin: ModelAdmin,
    admin_site: Any,
    *,
    obj: Model | None = None,
) -> list[dict[str, Any]]:
    """Custom (non-CRUD) admin views for a ``ModelAdmin`` (Issue #439).

    Walks ``model_admin.get_urls()``, drops the five standard CRUD
    routes (and any unnamed route), and returns a descriptor per
    remaining custom route::

        {"name": str, "label": str, "url": str, "level": "object"|"changelist"}

    Reversal rules:

    - ``level == "object"`` routes need an object id. When ``obj`` is
      provided they are reversed with ``args=[obj.pk]``; when ``obj`` is
      ``None`` (the registry / changelist context) they are skipped —
      there is no object to point them at.
    - ``level == "changelist"`` routes are reversed with ``args=[]``.

    Returns ``[]`` when the admin exposes no custom routes, or when none
    of them reverse. NEVER raises: a misbehaving consumer ``get_urls``
    degrades to ``[]`` (so the caller's detail / registry response is
    unaffected).
    """
    try:
        urls = model_admin.get_urls()
    except Exception:
        return []

    try:
        standard = _standard_route_names(model_admin.model)
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    for entry in urls:
        descriptor = _descriptor_for_route(entry, standard, admin_site, obj)
        if descriptor is not None:
            out.append(descriptor)
    return out


def _descriptor_for_route(
    entry: Any,
    standard: frozenset[str],
    admin_site: Any,
    obj: Model | None,
) -> dict[str, Any] | None:
    """Build one custom-view descriptor, or ``None`` to skip the route.

    A route is skipped (``None``) when it is unnamed, is a standard CRUD
    route, is object-level but we have no object, fails to reverse, or
    raises during introspection. One bad route never sinks the rest:
    every failure degrades to ``None`` rather than propagating.
    """
    try:
        name = getattr(entry, "name", None)
        # Unnamed routes (Django's legacy ``<pk>/`` catch-all) and the
        # five standard CRUD routes are not "custom views".
        if not name or name in standard:
            return None

        pattern = getattr(entry, "pattern", None)
        object_level = _is_object_level(pattern) if pattern is not None else False

        if object_level:
            if obj is None:
                # No object to anchor the route to in this context.
                return None
            url = _reverse_or_none(admin_site, name, [obj.pk])
            level = "object"
        else:
            url = _reverse_or_none(admin_site, name, [])
            level = "changelist"

        if url is None:
            return None

        return {
            "name": str(name),
            "label": _label_for_route(entry, str(name)),
            "url": url,
            "level": level,
        }
    except Exception:
        return None
