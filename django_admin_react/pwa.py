"""PWA surface: web app manifest + service worker (Issue #86).

Wire/UX contract: ``docs/ux/pwa.md``. The Security lane owns this
surface because its load-bearing properties are security ones:

- The **manifest** (``<mount>/web.manifest``) is served unauthenticated
  (the install prompt fires before login) and is computed at request
  time, but it carries **no per-user data** — only static/global values
  (mount-derived ``start_url``/``scope``, the AdminSite header, icons,
  theme colours from the client hint). An anonymous reader learns
  nothing they couldn't get from the static bundle.
- The **service worker** (``<mount>/sw.js``) is served with
  ``Service-Worker-Allowed: <mount>`` so its scope is exactly the mount
  and **never** sibling Django views. It honours ``Cache-Control:
  no-store`` (so the package's no-store API reads are never cached),
  never caches non-GET requests (mutation safety), and exposes a
  cache-purge message used on logout so read-cached payloads can't
  outlive the session (``pwa.md`` §5 — defense-in-depth atop session
  expiry).

Both views live **outside** ``api/`` because they're served at the
mount root, not under ``api/v1/``, and the manifest is intentionally
anonymous (unlike every API endpoint, which is staff-gated).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View

from django_admin_react import conf as dar_conf

# Re-use the API package's admin-site lookup (this repo implements no
# API; the registry helper lives there). The PWA only needs the active
# `AdminSite.name` for the manifest's start URL.
from django_admin_rest_api.api.registry import get_admin_site

# Theme colours keyed by the resolved colour scheme. Kept here (not in
# the SPA's CSS-var system) because the manifest is rendered server-side
# before any CSS loads; these are the install-banner / splash colours
# Android uses, and they only need to *approximate* the SPA theme.
_THEME_COLOURS = {
    "light": {"background": "#ffffff", "theme": "#2563eb"},
    "dark": {"background": "#0b0f19", "theme": "#3b82f6"},
}

_DEFAULT_ICONS: list[dict[str, str]] = [
    {"src": "static/dar/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "static/dar/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
    {
        "src": "static/dar/icons/icon-512-maskable.png",
        "sizes": "512x512",
        "type": "image/png",
        "purpose": "maskable",
    },
]


def _mount(request: HttpRequest, suffix: str) -> str:
    """Reconstruct the consumer's mount prefix from ``request.path``.

    The view is routed at ``<mount>/<suffix>`` (e.g. ``web.manifest``),
    so stripping the known suffix off ``request.path`` yields the mount.
    Mirrors ``views._mount_from_request`` but is local so this module
    has no import dependency on the SPA index view.
    """
    path = request.path
    idx = path.rfind(suffix)
    if idx == -1:
        return "/"
    return path[:idx] or "/"


def _resolved_scheme(request: HttpRequest) -> str:
    """Resolve light/dark from the ``Sec-CH-Prefers-Color-Scheme`` hint.

    Pairs with the theming client-hint path (``theming.md`` §2). Any
    value other than a case-insensitive ``"dark"`` resolves to light —
    the safe, neutral default when the hint is absent or unexpected.
    """
    hint = (request.headers.get("Sec-CH-Prefers-Color-Scheme") or "").strip().lower()
    return "dark" if hint == "dark" else "light"


class ManifestView(View):
    """``GET <mount>/web.manifest`` — the PWA web app manifest.

    Unauthenticated by design (the install prompt needs it pre-login).
    Carries no per-user data; every field is static or mount-/header-
    derived. ``Cache-Control: no-store`` is **not** set — the manifest
    is deliberately cacheable/network-first (``pwa.md`` §2.1).
    """

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        mount = _mount(request, "web.manifest")
        scheme = _resolved_scheme(request)
        colours = _THEME_COLOURS[scheme]

        admin_site = get_admin_site()
        site_header = getattr(admin_site, "site_header", None)
        name = dar_conf.PWA_NAME or (str(site_header) if site_header else "Django admin")
        short_name = dar_conf.PWA_SHORT_NAME or "Admin"
        icons = dar_conf.PWA_ICONS or _DEFAULT_ICONS

        manifest = {
            "name": name,
            "short_name": short_name,
            "start_url": mount,
            "scope": mount,
            "display": "standalone",
            "orientation": "any",
            "background_color": colours["background"],
            "theme_color": colours["theme"],
            "icons": icons,
        }
        response = JsonResponse(manifest, content_type="application/manifest+json")
        # Vary on the client hint so a light/dark cache entry doesn't
        # serve the wrong splash colours to the other scheme.
        response["Vary"] = "Sec-CH-Prefers-Color-Scheme"
        return response


class ServiceWorkerView(View):
    """``GET <mount>/sw.js`` — the hand-rolled service worker.

    Served with ``Service-Worker-Allowed: <mount>`` so the SW can claim
    the whole mount as its scope (a SW's default scope is its own path;
    the header widens it to the mount root). The JS is rendered from a
    template with the mount injected so the SW's fetch interception is
    bounded to the mount and never touches sibling Django views.
    """

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        mount = _mount(request, "sw.js")
        response = render(
            request,
            "admin_react/sw.js",
            {"mount": mount},
            content_type="application/javascript",
        )
        # Allow the SW to control the entire mount, not just ``<mount>/sw.js``.
        response["Service-Worker-Allowed"] = mount
        # The SW script itself should not be cached aggressively — a new
        # deploy must be able to ship a new SW. ``no-cache`` (revalidate)
        # not ``no-store`` so the browser's SW update check still works.
        response["Cache-Control"] = "no-cache"
        return response
