"""System checks for django_admin_react (#667).

Registered against ``django.core.checks`` so common misconfigurations
surface at ``manage.py check`` (and on every ``runserver`` boot) with an
actionable hint — instead of a lazy ``ValueError`` on first settings
access, a runtime 500, or a silent template fallback.

What we validate:

- ``django_admin_rest_api`` is installed (the package implements no API of
  its own — every JSON endpoint lives in that sibling package).
- ``DJANGO_ADMIN_REACT["ADMIN_SITE"]`` (dotted path) actually imports.
- ``DJANGO_ADMIN_REACT`` has no unknown keys (the same guard ``conf._load``
  enforces lazily — surfaced here at startup as a clean check error).
- ``API_URL_PREFIX`` mounting is coherent: when it is set, the package
  skips its inline ``api/v1/`` include, so the consumer must mount
  ``django_admin_rest_api.urls`` themselves — a Warning reminds them.
- The built SPA bundle / Vite manifest exists (a Warning, not an Error —
  the package serves a friendly "not built" shell, and the manifest is
  absent in a source checkout / before ``pnpm build``).

Severities follow Django's convention: an ``Error`` blocks (the package
cannot work); a ``Warning`` is a likely-misconfiguration heads-up that
does not hard-block.
"""

from __future__ import annotations

from typing import Any

from django.core.checks import Error
from django.core.checks import Warning as CheckWarning

# Stable check IDs (Django convention ``<app_label>.E/W###``) so a consumer
# can silence a specific one via ``SILENCED_SYSTEM_CHECKS`` if they must.
ID_REST_API_MISSING = "django_admin_react.E001"
ID_ADMIN_SITE_IMPORT = "django_admin_react.E002"
ID_UNKNOWN_SETTINGS = "django_admin_react.E003"
ID_API_PREFIX_MOUNT = "django_admin_react.W001"
ID_BUNDLE_MISSING = "django_admin_react.W002"


def check_django_admin_react(app_configs: Any, **kwargs: Any) -> list[Any]:
    """Run every package configuration check.

    Registered as a single callable (rather than many) so the import
    surface stays small and the ordering is explicit. ``app_configs`` /
    ``kwargs`` are the Django check-framework signature; unused here
    because the checks are global to the package, not per-app.
    """
    errors: list[Any] = []
    errors.extend(_check_rest_api_installed())
    errors.extend(_check_admin_site_imports())
    errors.extend(_check_settings_keys())
    errors.extend(_check_api_prefix_coherence())
    errors.extend(_check_bundle_built())
    return errors


def _check_rest_api_installed() -> list[Any]:
    from django.apps import apps as django_apps

    if django_apps.is_installed("django_admin_rest_api"):
        return []
    return [
        Error(
            "'django_admin_rest_api' is not in INSTALLED_APPS.",
            hint=(
                "django-admin-react is a React SPA over django-admin-rest-api "
                "and implements no API of its own. Add 'django_admin_rest_api' "
                "to INSTALLED_APPS (it ships as a dependency)."
            ),
            id=ID_REST_API_MISSING,
        )
    ]


def _check_admin_site_imports() -> list[Any]:
    from django.utils.module_loading import import_string

    from django_admin_react import conf as dar_conf

    dotted = dar_conf.ADMIN_SITE
    try:
        import_string(dotted)
    except ImportError as exc:
        return [
            Error(
                f"DJANGO_ADMIN_REACT['ADMIN_SITE'] = {dotted!r} could not be imported " f"({exc}).",
                hint=(
                    "Point ADMIN_SITE at the dotted path of your AdminSite "
                    "instance (e.g. 'myproject.admin.site' or the default "
                    "'django.contrib.admin.site')."
                ),
                id=ID_ADMIN_SITE_IMPORT,
            )
        ]
    return []


def _check_settings_keys() -> list[Any]:
    from django.conf import settings as django_settings

    from django_admin_react.conf import DEFAULTS

    overrides = getattr(django_settings, "DJANGO_ADMIN_REACT", {}) or {}
    unknown = sorted(set(overrides) - set(DEFAULTS))
    if not unknown:
        return []
    return [
        Error(
            "Unknown DJANGO_ADMIN_REACT key(s): " + ", ".join(unknown) + ".",
            hint=("Remove the typo'd key(s). Valid keys are: " + ", ".join(sorted(DEFAULTS)) + "."),
            id=ID_UNKNOWN_SETTINGS,
        )
    ]


def _check_api_prefix_coherence() -> list[Any]:
    from django_admin_react import conf as dar_conf

    prefix = dar_conf.API_URL_PREFIX
    if prefix is None:
        # Inline mount is active; the package mounts the API itself. Nothing
        # the consumer must do.
        return []
    # The override is set, so `django_admin_react.urls` skips the inline
    # `api/v1/` include — the consumer MUST mount the REST API themselves at
    # that prefix or every SPA data call 404s.
    return [
        CheckWarning(
            f"DJANGO_ADMIN_REACT['API_URL_PREFIX'] = {prefix!r} is set, so this "
            "package does NOT mount the REST API inline.",
            hint=(
                "Mount the sibling API yourself at that prefix, e.g.\n"
                f"    path({prefix!r}, include('django_admin_rest_api.api.urls'))\n"
                "or unset API_URL_PREFIX to use the package's inline 'api/v1/' mount."
            ),
            id=ID_API_PREFIX_MOUNT,
        )
    ]


def _check_bundle_built() -> list[Any]:
    # Imported lazily so the check module has no import-time dependency on
    # the view layer.
    from django_admin_react.views import _MANIFEST_PATH

    if _MANIFEST_PATH.is_file():
        return []
    return [
        CheckWarning(
            "The built SPA bundle / Vite manifest was not found at " f"{_MANIFEST_PATH}.",
            hint=(
                "Install the published wheel (which ships the built bundle), or "
                "build the frontend from source with 'pnpm --dir frontend build'. "
                "Until then the SPA shell renders a 'not built yet' page."
            ),
            id=ID_BUNDLE_MISSING,
        )
    ]
