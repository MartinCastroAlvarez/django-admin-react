"""AdminSite introspection helpers.

The package looks up ``ModelAdmin`` instances **only** through the
configured admin site's ``_registry`` (rule 3 in ``SECURITY.md`` §3).
Client-provided ``app_label`` / ``model_name`` strings are never used
to ``import_string`` a model directly.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.apps import apps
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.db.models import Model
from django.http import HttpRequest
from django.utils.module_loading import import_string


def get_admin_site() -> AdminSite:
    """Resolve the configured admin site instance.

    Configured via ``settings.DJANGO_ADMIN_REACT["ADMIN_SITE"]``;
    defaults to ``django.contrib.admin.site``. Resolution is lazy: we
    look up the dotted path each call so tests can override settings via
    Django's standard ``override_settings`` decorator without having to
    reload this module.
    """
    from django_admin_react import conf

    dotted_path: str = conf.ADMIN_SITE
    site = import_string(dotted_path)
    if not isinstance(site, AdminSite):
        raise TypeError(
            "DJANGO_ADMIN_REACT['ADMIN_SITE'] must point to an AdminSite "
            f"instance; got {type(site).__name__} at {dotted_path!r}."
        )
    return site


def iter_visible_models(
    admin_site: AdminSite, request: HttpRequest
) -> Iterable[tuple[type[Model], ModelAdmin]]:
    """Yield (model, model_admin) pairs the request may view.

    Filters by:

    - ``ModelAdmin.has_module_permission(request)`` — gate per app.
    - ``ModelAdmin.has_view_permission(request)`` — gate per model.

    Both must return truthy. Order is the registration order in
    ``_registry`` (Django preserves dict insertion order).
    """
    for model, model_admin in admin_site._registry.items():
        if not model_admin.has_module_permission(request):
            continue
        if not model_admin.has_view_permission(request):
            continue
        yield model, model_admin


def _model_permissions(model_admin: ModelAdmin, request: HttpRequest) -> dict[str, bool]:
    """The four ``has_*_permission`` answers, as plain booleans."""
    return {
        "view": bool(model_admin.has_view_permission(request)),
        "add": bool(model_admin.has_add_permission(request)),
        "change": bool(model_admin.has_change_permission(request)),
        "delete": bool(model_admin.has_delete_permission(request)),
    }


def _model_entry(model: type[Model], model_admin: ModelAdmin, request: HttpRequest) -> dict:
    meta = model._meta
    return {
        "app_label": meta.app_label,
        "model_name": meta.model_name,
        "object_name": meta.object_name,
        "verbose_name": str(meta.verbose_name),
        "verbose_name_plural": str(meta.verbose_name_plural),
        "permissions": _model_permissions(model_admin, request),
    }


def _user_payload(request: HttpRequest) -> dict:
    user = request.user
    full_name = (user.get_full_name() or "").strip() if hasattr(user, "get_full_name") else ""
    display_name = full_name or user.get_username()
    return {
        "id": user.pk,
        "username": user.get_username(),
        "is_staff": bool(getattr(user, "is_staff", False)),
        "is_superuser": bool(getattr(user, "is_superuser", False)),
        "display_name": display_name,
    }


def _mount_from_request(request: HttpRequest) -> str:
    """Best-effort recovery of the consumer-chosen mount prefix.

    The view's URL pattern is fixed inside this package (``api/v1/registry/``),
    so anything in front of that on ``request.path`` is the mount the
    consumer configured (`ARCHITECTURE.md` §4.5).
    """
    suffix = "api/v1/registry/"
    path = request.path
    idx = path.rfind(suffix)
    if idx == -1:
        # Should not happen — the URL config routed us here. Fall back to '/'.
        return "/"
    return path[:idx] or "/"


def build_registry_payload(admin_site: AdminSite, request: HttpRequest) -> dict:
    """Build the ``GET /api/v1/registry/`` response body.

    The shape is documented in ``docs/api-contract.md`` §2.
    """
    apps_payload: dict[str, dict] = {}
    for model, model_admin in iter_visible_models(admin_site, request):
        app_label = model._meta.app_label
        bucket = apps_payload.setdefault(
            app_label,
            {
                "app_label": app_label,
                "verbose_name": _app_verbose_name(app_label),
                "models": [],
            },
        )
        bucket["models"].append(_model_entry(model, model_admin, request))

    return {
        "mount": _mount_from_request(request),
        "user": _user_payload(request),
        "apps": list(apps_payload.values()),
    }


def _app_verbose_name(app_label: str) -> str:
    """Return the human-readable app name, falling back to the label."""
    try:
        return str(apps.get_app_config(app_label).verbose_name)
    except LookupError:
        # Model whose app isn't installed should never reach us, but
        # don't crash if it does.
        return app_label
