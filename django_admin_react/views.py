"""SPA entry point view.

Serves the built React single-page app to authenticated staff. The
SPA's bundled assets ship with the package under
``django_admin_react/static/admin_react/`` and a Django template at
``django_admin_react/templates/admin_react/index.html`` references
them via a Vite-emitted manifest.

The view's only jobs are:

1. Enforce the same authentication gate as the rest of the package
   (active + staff, or whatever ``AdminSite.has_permission`` says).
2. Render ``index.html`` with the resolved mount point and the
   bundle filenames from the Vite manifest so the SPA can construct
   API URLs without hardcoding (`ARCHITECTURE.md` §4.5).

This view never returns 404 for "no manifest yet" — a consumer
who installed the wheel always has a manifest. In development the
helper :func:`_load_manifest` returns ``None`` and the template
falls back to a friendly "the SPA is not built; run pnpm build:vite"
message, so a contributor running ``runserver`` without having built
the frontend gets a clear next step instead of a JS error.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import NoReverseMatch
from django.urls import reverse
from django.views.generic import View

from django_admin_react import conf as dar_conf
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site

# Path the Vite build writes its manifest to (matches
# ``frontend/apps/web/vite.config.ts``'s build.outDir + manifest).
_STATIC_ROOT: Path = Path(__file__).resolve().parent / "static" / "admin_react"
_MANIFEST_PATH: Path = _STATIC_ROOT / ".vite" / "manifest.json"
_ENTRY_KEY: str = "index.html"


class SpaIndexView(View):
    """Serves the built React SPA at any URL the consumer mounts.

    Per the wire contract, the same auth gate that protects the API
    protects this view too — there's no point serving a SPA shell to
    a non-staff user only to have every API call return 403.
    """

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # noqa: ARG002 — args/kwargs only present to satisfy CBV signature.
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return _redirect_to_login(request)

        # Force CSRF cookie so the SPA can read it before any unsafe
        # method (the fetch client attaches it as ``X-CSRFToken``).
        get_token(request)

        return render(
            request,
            "admin_react/index.html",
            {
                "mount_point": _mount_from_request(request),
                "bundle": _load_manifest_entry(),
                "brand_title": _resolve_brand_title(admin_site),
                "brand_logo_url": dar_conf.BRAND_LOGO_URL,
            },
        )


# --------------------------------------------------------------------------- #
# Manifest loading                                                            #
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _load_manifest_entry() -> dict[str, Any] | None:
    """Read the Vite manifest and return the entry record, or ``None``.

    Cached in-process — the manifest file is immutable for a given
    deploy. If you need to test a rebuilt SPA in the same Django
    process, call ``_load_manifest_entry.cache_clear()``.
    """
    if not _MANIFEST_PATH.is_file():
        return None
    try:
        manifest: dict[str, Any] = json.loads(_MANIFEST_PATH.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entry = manifest.get(_ENTRY_KEY)
    if not isinstance(entry, dict):
        return None
    return entry


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _resolve_brand_title(admin_site: Any) -> str:
    """Compute the SPA brand title.

    Resolution order:

    1. ``DJANGO_ADMIN_REACT["BRAND_TITLE"]`` — explicit consumer override.
    2. ``admin_site.site_header`` — what the consumer already set on
       their custom ``AdminSite`` for the legacy admin. Reusing it
       keeps both admins in sync without a second setting.
    3. Literal ``"Django Admin"`` — last-resort fallback, mirrors the
       prior hardcoded ``<title>`` in the template.
    """
    configured = dar_conf.BRAND_TITLE
    if isinstance(configured, str) and configured.strip():
        return configured
    site_header = getattr(admin_site, "site_header", None)
    if site_header:
        return str(site_header)
    return "Django Admin"


def _mount_from_request(request: HttpRequest) -> str:
    """Reconstruct the consumer-chosen mount prefix from ``request.path``.

    The SPA index view is the catch-all under the mount, so
    ``request.path`` is *already* a path under the mount. We can
    take everything up to the last path segment that the SPA itself
    serves and treat it as the mount. The simplest stable signal is
    the URL that ``urls.py`` registered — but to stay loose-coupled,
    we just return everything up to and including the FIRST segment.
    The SPA's React Router uses this as its basename.
    """
    path = request.path
    if not path.startswith("/"):
        return "/"
    # First path component after the leading slash.
    parts = path.split("/", 2)
    if len(parts) < 3:
        return path if path.endswith("/") else path + "/"
    return f"/{parts[1]}/"


def _redirect_to_login(request: HttpRequest) -> HttpResponse:
    """Redirect unauthenticated requests to the configured login URL.

    Resolution order (Issue #114):

    1. ``<configured AdminSite>:login`` — reverse against the same
       site the consumer registered. A consumer who customised
       ``DJANGO_ADMIN_REACT["ADMIN_SITE"]`` to a site at ``/admin/``
       gets ``/admin/login/`` automatically; this works whether or
       not the consumer set ``settings.LOGIN_URL``.
    2. ``settings.LOGIN_URL`` — honoured when the consumer
       explicitly configured an authentication flow outside the
       admin (e.g. their own SSO endpoint). Used regardless of
       whether the URL resolves; the consumer owns it.
    3. ``admin:login`` — last-resort reverse on Django's stock
       admin site.
    4. ``/accounts/login/`` — Django's default. Last resort; rarely
       useful because many real apps route ``/accounts/`` to DRF.

    The ``next`` query parameter brings the user back to the SPA
    after login.
    """
    from django_admin_react.api.registry import get_admin_site

    login_url: str | None = None

    # 1. Consumer's configured AdminSite.
    try:
        admin_site = get_admin_site()
        site_namespace = getattr(admin_site, "name", None) or "admin"
        login_url = reverse(f"{site_namespace}:login")
    except (NoReverseMatch, Exception):  # noqa: BLE001 — defensive
        login_url = None

    # 2. Explicit settings.LOGIN_URL — but only when the consumer
    #    explicitly customised it. Django sets a default
    #    `/accounts/login/` so we treat that exact value as "not
    #    customised" and prefer the AdminSite path.
    if login_url is None:
        configured = getattr(settings, "LOGIN_URL", None)
        if configured and configured != "/accounts/login/":
            login_url = str(configured)

    # 3. Stock admin login.
    if login_url is None:
        try:
            login_url = reverse("admin:login")
        except NoReverseMatch:
            login_url = "/accounts/login/"

    return redirect(f"{login_url}?next={request.path}")
