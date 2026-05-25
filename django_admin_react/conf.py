"""Lazy settings wrapper for django_admin_react.

All package settings live under a single optional dict
``settings.DJANGO_ADMIN_REACT``. Defaults are applied lazily so that
adding the app to ``INSTALLED_APPS`` does not require a settings entry.

Usage in package code:

    from django_admin_react.conf import settings
    settings.MAX_PAGE_SIZE

Nothing in the package should read ``django.conf.settings.DJANGO_ADMIN_REACT``
directly — go through this module so defaults are consistent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings as django_settings

DEFAULTS: dict[str, Any] = {
    "ADMIN_SITE": "django.contrib.admin.site",
    "DEFAULT_PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 200,
    "ENABLE_PROFILING": False,
}


@dataclass(frozen=True)
class _PackageSettings:
    """Resolved package settings.

    Real implementation lands in PR #2. For now this is a stub so other
    modules can import the typed attribute names.
    """

    ADMIN_SITE: str = DEFAULTS["ADMIN_SITE"]
    DEFAULT_PAGE_SIZE: int = DEFAULTS["DEFAULT_PAGE_SIZE"]
    MAX_PAGE_SIZE: int = DEFAULTS["MAX_PAGE_SIZE"]
    ENABLE_PROFILING: bool = DEFAULTS["ENABLE_PROFILING"]


def _load() -> _PackageSettings:
    user_overrides = getattr(django_settings, "DJANGO_ADMIN_REACT", {}) or {}
    merged = {**DEFAULTS, **user_overrides}
    # Reject unknown keys defensively to surface typos early.
    unknown = set(merged) - set(DEFAULTS)
    if unknown:
        raise ValueError("Unknown DJANGO_ADMIN_REACT keys: " + ", ".join(sorted(unknown)))
    return _PackageSettings(**merged)


# Lazily resolve on first access; cache.
_cached: _PackageSettings | None = None


def __getattr__(name: str) -> Any:  # pragma: no cover — thin shim
    global _cached
    if _cached is None:
        _cached = _load()
    return getattr(_cached, name)
