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
    # The list page size derives from the model's
    # ``ModelAdmin.list_per_page`` (Django's changelist source of truth,
    # Rule #1 / #281), so the SPA pages like the HTML admin with no extra
    # setting. ``DEFAULT_PAGE_SIZE`` is the fallback only when
    # ``list_per_page`` is missing / invalid. ``MAX_PAGE_SIZE`` always caps
    # ``?page_size`` (a DoS guard).
    "DEFAULT_PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 200,
    "ENABLE_PROFILING": False,
    # Branding — consumer overrides surface in the SPA shell. Both are
    # rendered server-side into the SPA index template so the SPA
    # picks them up on first paint (no FOUC).
    #
    # ``BRAND_TITLE``      — optional override for *both* the sidebar
    #                        header and the browser-tab title. ``None``
    #                        (default) derives them from the AdminSite,
    #                        mirroring Django admin: ``site_header`` →
    #                        sidebar header, ``site_title`` → tab title
    #                        (falling back to ``site_header``), else the
    #                        package name (#281). A consumer who already
    #                        set ``site_header`` / ``site_title`` on their
    #                        ``AdminSite`` needs no branding setting at all.
    #                        Plain text; no HTML.
    # ``BRAND_LOGO_URL``   — optional override for the logo / favicon URL,
    #                        written into the SPA's ``<link rel="icon">``.
    #                        ``None`` (default) reads ``site_logo`` off the
    #                        configured ``AdminSite`` if the consumer set
    #                        that attribute (#281), else keeps the no-op
    #                        ``data:,`` placeholder. Either an absolute URL
    #                        or a path under your ``STATIC_URL``.
    "BRAND_TITLE": None,
    "BRAND_LOGO_URL": None,
    # ``PRIMARY_COLOR`` — the accent color for primary buttons, links, and
    # active states (#437). Injected into the SPA template as the
    # ``--dar-primary`` CSS variable so a consumer can brand the admin with
    # no React rebuild. Must be a hex color (``#rgb`` / ``#rgba`` /
    # ``#rrggbb`` / ``#rrggbbaa``); anything else is rejected at render and
    # falls back to this default, since the value is written into a
    # ``<style>`` block and must not be able to inject CSS.
    "PRIMARY_COLOR": "#2563eb",
    # ``REACT_LOGIN`` — opt-in React-rendered login (Issue #167).
    # Default ``False`` keeps today's behavior: ``SpaIndexView``
    # redirects anonymous / unauthorized users to Django's HTML login
    # (or the package's own ``<mount>/login/`` page). When ``True``,
    # the SPA shell is served to anonymous users (with the CSRF cookie
    # set) so the React app can render its own login form, which POSTs
    # to ``/api/v1/login/``. The auth *mechanism* is unchanged — still
    # Django's ``authenticate``/``login`` behind the JSON endpoint
    # (`api/views/auth.py`); only the UI surface differs. The shell
    # carries no user data, so serving it to anonymous users discloses
    # nothing the static bundle wouldn't, and every data API call still
    # returns 403 until the user authenticates.
    "REACT_LOGIN": False,
    # PWA (Issue #86) — all optional; sane defaults make the manifest
    # work with zero config. See ``django_admin_react/pwa.py`` +
    # ``docs/ux/pwa.md``.
    #
    # ``PWA_NAME``       — installed-app name. ``None`` (default) falls
    #                      back to the AdminSite ``site_header``, then
    #                      ``"Django admin"``.
    # ``PWA_SHORT_NAME`` — home-screen label. Defaults to ``"Admin"``.
    # ``PWA_ICONS``      — list of ``{src, sizes, type[, purpose]}``
    #                      dicts. ``None`` (default) uses the shipped
    #                      192/512/maskable set under
    #                      ``static/dar/icons/``.
    # ``API_URL_PREFIX`` — absolute URL prefix the SPA calls for every
    # JSON request (#559). Default ``None`` keeps the inline include the
    # package ships today (`<spa-mount>/api/v1/`), so existing consumers
    # are unaffected. Override when the consumer mounts
    # ``django_admin_rest_api.urls`` separately and the SPA should talk
    # to **that** mount instead — for example
    # ``DJANGO_ADMIN_REACT = {"API_URL_PREFIX": "/api/api/v1/"}`` lets
    # the SPA and any other client share a single REST mount. When set,
    # `django_admin_react.urls` skips the inline `api/v1/` include so
    # there is no double-mount.
    "API_URL_PREFIX": None,
    "PWA_NAME": None,
    "PWA_SHORT_NAME": None,
    "PWA_ICONS": None,
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
    BRAND_TITLE: str | None = DEFAULTS["BRAND_TITLE"]
    BRAND_LOGO_URL: str | None = DEFAULTS["BRAND_LOGO_URL"]
    PRIMARY_COLOR: str = DEFAULTS["PRIMARY_COLOR"]
    REACT_LOGIN: bool = DEFAULTS["REACT_LOGIN"]
    API_URL_PREFIX: str | None = DEFAULTS["API_URL_PREFIX"]
    PWA_NAME: str | None = DEFAULTS["PWA_NAME"]
    PWA_SHORT_NAME: str | None = DEFAULTS["PWA_SHORT_NAME"]
    PWA_ICONS: list[dict[str, str]] | None = DEFAULTS["PWA_ICONS"]


def _load() -> _PackageSettings:
    """Merge the consumer's overrides with ``DEFAULTS``.

    Unknown keys raise ``ValueError`` so a typo in
    ``settings.DJANGO_ADMIN_REACT`` is caught at startup rather than
    silently ignored. Returns an immutable ``_PackageSettings``.
    """
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
    """Module-level ``__getattr__`` (PEP 562) so callers can write
    ``from django_admin_react.conf import settings`` or
    ``conf.MAX_PAGE_SIZE`` without a separate accessor.

    First access triggers ``_load()`` and caches the result; later
    accesses return cached attributes. Reload requires re-importing
    the module (matches Django's own settings semantics).
    """
    global _cached
    if _cached is None:
        _cached = _load()
    return getattr(_cached, name)
