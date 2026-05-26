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
    """Single ``models[]`` element for the registry response.

    Wire shape is documented in ``docs/api-contract.md`` §2. Only
    metadata + the four ``has_*_permission`` booleans go on the wire;
    no model field schemas, no row counts — those are detail/list
    endpoint responsibilities.
    """
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
    """``user`` block on the registry response (contract §2).

    Exposes only data the user already knows about themselves: pk,
    username, display name, ``is_staff``, ``is_superuser``. No email,
    no group memberships, no permission codenames, no last-login
    timestamp — the SPA does not need them and the registry endpoint
    must stay deny-by-default (``SECURITY.md`` §3 rule 12).

    ``getattr(user, "is_active", False)`` style defaults are used so
    a custom user model missing an attribute degrades to "no" rather
    than raising.
    """
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

    Walks ``admin_site.get_app_list(request)`` rather than iterating
    ``_registry`` directly, so consumer overrides of
    ``AdminSite.get_app_list`` (custom groupings, curated model lists,
    operator-meaningful section names) are honored 1:1.
    ``get_app_list`` already filters by ``has_module_permission`` +
    per-model ``has_view_permission`` inside Django — we inherit that
    filtering; no parallel permission gate (rule 1).

    Each ``apps[]`` entry carries:

    - ``name``: human-readable group name from ``get_app_list``.
    - ``app_label``: the group's identifier — Django's real label
      when the default ``get_app_list`` runs, or the consumer's
      synthetic label when overridden.
    - ``verbose_name``: alias of ``name`` for backwards compatibility
      with clients of earlier ``0.1.0a*`` responses.
    - ``is_group``: ``True`` when ``app_label`` is *not* one of the
      installed Django apps (i.e. the consumer coined it inside their
      override); ``False`` otherwise.
    - ``models``: per-model entries, each carrying ``real_app_label``
      (the underlying ``model._meta.app_label``) so the SPA can
      construct URLs as ``<mount>/api/v1/<real_app_label>/<model_name>/``
      regardless of how the group was labelled.

    See issue #138 for the design discussion; the contract change
    landed in PR #140.
    """
    real_app_labels: frozenset[str] = frozenset(c.label for c in apps.get_app_configs())
    apps_payload: list[dict] = []
    for app in admin_site.get_app_list(request):
        group_label = app["app_label"]
        group_name = str(app.get("name") or group_label)
        is_group = group_label not in real_app_labels
        models_payload: list[dict] = []
        for raw_entry in app["models"]:
            # ``get_app_list`` populates each entry with the model class
            # under the ``"model"`` key (Django ≥3.1). Re-resolve to
            # ``(model, model_admin)`` via ``_registry`` so the per-model
            # entry comes from ``_model_entry`` (rule 1: ModelAdmin is
            # the source of truth for permissions / metadata).
            model = raw_entry.get("model")
            if model is None:
                continue
            model_admin = admin_site._registry.get(model)
            if model_admin is None:
                # Defensive: ``get_app_list`` surfaced a model not in
                # ``_registry``. Skip — surfacing a model the package
                # can't address via its URL space would be misleading.
                continue
            # Django's ``get_app_list`` includes a model when the user
            # has *any* perm on it (view OR add OR change OR delete) —
            # the HTML admin's sidebar carries the entry even if the
            # list view would 403. For the SPA the registry IS the nav
            # surface, so a model without view permission would just
            # render as a broken tile (the list endpoint returns 403).
            # Apply the same per-model ``has_view_permission`` gate the
            # original ``iter_visible_models`` enforced (rule 5 in
            # ``SECURITY.md`` §3).
            if not model_admin.has_view_permission(request):
                continue
            entry = _model_entry(model, model_admin, request)
            entry["real_app_label"] = model._meta.app_label
            entry["app_label"] = group_label
            models_payload.append(entry)
        # Don't surface an empty group — matches Django's
        # ``get_app_list`` behavior, which drops apps whose models list
        # is empty after permission filtering.
        if not models_payload:
            continue
        apps_payload.append(
            {
                "name": group_name,
                "app_label": group_label,
                "verbose_name": group_name,
                "is_group": is_group,
                "models": models_payload,
            }
        )

    return {
        "mount": _mount_from_request(request),
        "user": _user_payload(request),
        "apps": apps_payload,
    }


def _app_verbose_name(app_label: str) -> str:
    """Return the human-readable app name, falling back to the label."""
    try:
        return str(apps.get_app_config(app_label).verbose_name)
    except LookupError:
        return app_label


# Top-level URL segments mounted directly under ``/api/v1/`` by this
# package. Resolving a per-app endpoint against any of these
# ``app_label`` values would either shadow the package's own view
# (if Django's URL resolver order favors the literal route, which it
# does) or, worse, surface a consumer model whose URL the SPA can
# never reach. Treat the segment as reserved and 404 instead — same
# posture as an unregistered model. Closes issue #93.
RESERVED_APP_LABELS: frozenset[str] = frozenset(
    {"registry", "schema", "session", "login", "logout"}
)


def resolve_model(
    admin_site: AdminSite,
    request: HttpRequest,
    app_label: str,
    model_name: str,
) -> tuple[type[Model], ModelAdmin] | None:
    """Look up a registered ``(model, model_admin)`` by client-given strings.

    Client-provided ``app_label`` and ``model_name`` are **never** trusted.
    They are resolved through ``AdminSite._registry`` (rule 3 in
    ``SECURITY.md`` §3) and the resolution is gated by
    ``has_module_permission`` and ``has_view_permission``.

    Reserved-segment guard (issue #93): if ``app_label`` matches one of
    the package's top-level URL segments (``registry``, ``schema``,
    ``session``), the resolution returns ``None`` even when a
    consumer happens to register a Django app with that label. The
    package's own view wins the URL route; surfacing the consumer's
    model would only confuse the SPA.

    Returns ``None`` if the model is not registered or the request is not
    permitted to view it. The caller must convert that to a 404, per
    ``ACCEPTANCE.md`` §3.1 B-7 and §4.3 S-11/S-12.
    """
    if not isinstance(app_label, str) or not isinstance(model_name, str):
        return None
    if app_label.lower() in RESERVED_APP_LABELS:
        return None
    target = (app_label.lower(), model_name.lower())
    for model, model_admin in admin_site._registry.items():
        meta = model._meta
        if (meta.app_label, meta.model_name) != target:
            continue
        if not model_admin.has_module_permission(request):
            return None
        if not model_admin.has_view_permission(request):
            return None
        return model, model_admin
    return None


def model_permissions(model_admin: ModelAdmin, request: HttpRequest) -> dict[str, bool]:
    """Public alias for the four ``has_*_permission`` booleans."""
    return _model_permissions(model_admin, request)


def save_options(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model | None = None,
) -> dict[str, bool]:
    """Visibility of the four Django save-flow buttons for this view (#154).

    Mirrors the logic Django's ``admin_modify.submit_row`` template tag
    applies, restricted to the two views this package serves:

    - ``obj is not None`` → **change view** (``add=False, change=True``).
    - ``obj is None``     → **add/create view** (``add=True, change=False``).

    We compute the flags from ``ModelAdmin`` permission methods +
    ``ModelAdmin.save_as`` rather than rendering the admin template, so
    the package never depends on the admin template context. The flag
    set is the source of truth for which buttons the SPA renders; the
    SPA never invents a save routing the backend wouldn't allow.

    Returned keys (all booleans):

    - ``show_save`` — the plain "Save" button.
    - ``show_save_and_continue`` — "Save and continue editing".
    - ``show_save_and_add_another`` — "Save and add another".
    - ``show_save_as_new`` — "Save as new" (change view only, and only
      when ``ModelAdmin.save_as`` is True).
    - ``save_as`` — the raw ``ModelAdmin.save_as`` flag, surfaced so the
      SPA knows whether a "Save as new" POST creates a fresh object.
    - ``save_as_continue`` — the raw ``ModelAdmin.save_as_continue``
      flag (default True): after a "Save as new", whether the SPA
      lands on the new object's change view (True) or the changelist
      (False).

    ``has_editable_inline_admin_formsets`` is **not** factored in here
    (the package's inline write-half is tracked under #54). Until that
    lands, ``can_save`` reduces to the object-level change/add
    permission, which is correct for models without editable inlines —
    the overwhelming common case.
    """
    is_change = obj is not None
    is_add = not is_change
    save_as = bool(getattr(model_admin, "save_as", False))
    save_as_continue = bool(getattr(model_admin, "save_as_continue", True))

    has_add = bool(model_admin.has_add_permission(request))
    has_change = bool(model_admin.has_change_permission(request, obj))
    has_view = bool(model_admin.has_view_permission(request, obj))

    # Django: can_save = (has_change and change) or (has_add and add).
    can_save = (has_change and is_change) or (has_add and is_add)
    # Django: can_save_and_add_another = has_add and (not save_as or add) and can_save.
    can_add_another = has_add and (not save_as or is_add) and can_save
    # Django: can_save_and_continue = can_save and has_view (not is_popup; we never pop up).
    can_continue = can_save and has_view
    # Django: show_save_as_new = has_change and change and save_as.
    show_save_as_new = has_change and is_change and save_as

    return {
        "show_save": can_save,
        "show_save_and_continue": can_continue,
        "show_save_and_add_another": can_add_another,
        "show_save_as_new": show_save_as_new,
        "save_as": save_as,
        "save_as_continue": save_as_continue,
    }


def password_change_form_class(model_admin: ModelAdmin) -> type | None:
    """Return the admin's declared password-change form class, or ``None``.

    Django's ``UserAdmin`` declares ``change_password_form`` (default
    ``django.contrib.auth.forms.AdminPasswordChangeForm``) and registers a
    dedicated ``<id>/password/`` view; a plain ``ModelAdmin`` does neither.
    We treat the presence of a ``change_password_form`` attribute as the
    signal that this admin intends password-set support — and reuse *that*
    form, so the package never invents its own password handling (rule 1:
    ``ModelAdmin`` is the only source of truth). Models whose admin lacks
    the attribute have no password sub-resource (the caller 404s, exactly
    as Django's router 404s ``/password/`` for a non-``UserAdmin`` model).
    """
    form_class = getattr(model_admin, "change_password_form", None)
    return form_class if isinstance(form_class, type) else None


def password_change_meta(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model,
) -> dict[str, bool]:
    """Detail-payload block describing the password-set affordance (#252).

    ``supported`` is ``True`` only when the admin exposes a password-change
    form **and** the request holds change permission on the object — so the
    SPA shows "Set password" exactly when the POST would be accepted, never
    a button that 403s. No password material is ever surfaced here; this is
    purely a capability flag (the field itself stays hidden by the
    sensitive-name denylist).
    """
    return {
        "supported": bool(
            password_change_form_class(model_admin) is not None
            and model_admin.has_change_permission(request, obj)
        ),
    }
