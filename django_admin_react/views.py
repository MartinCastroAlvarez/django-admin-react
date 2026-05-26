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
from typing import cast

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import NoReverseMatch
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.http import urlencode
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
        # Default: redirect anonymous / unauthorized users to the HTML
        # login. When the consumer opts into the React login
        # (``DJANGO_ADMIN_REACT["REACT_LOGIN"]``), serve the SPA shell
        # instead so the React app renders its own login form (which
        # POSTs to ``/api/v1/login/``). The shell holds no user data —
        # bundle loader + mount/brand meta only — so anonymous access
        # discloses nothing the static assets wouldn't, and every data
        # API call still 403s until login.
        if not is_admin_user(request, admin_site=admin_site) and not dar_conf.REACT_LOGIN:
            return _redirect_to_login(request)

        # Force CSRF cookie so the SPA can read it before any unsafe
        # method (the fetch client attaches it as ``X-CSRFToken``). Runs
        # for anonymous users too under ``REACT_LOGIN`` so the login
        # POST carries a valid CSRF token.
        get_token(request)

        response = render(
            request,
            "admin_react/index.html",
            {
                "mount_point": _mount_from_request(request),
                "bundle": _load_manifest_entry(),
                "brand_title": _resolve_brand_title(admin_site),
                "brand_logo_url": dar_conf.BRAND_LOGO_URL,
            },
        )
        # The SPA shell must never be cached: it references the
        # hash-named bundle (``index-<hash>.js``), so a stale shell
        # points at an asset filename that no longer exists after a
        # rebuild — the browser then boots an old/broken SPA. The
        # bundle assets themselves are immutable + hash-named, so they
        # stay cacheable forever (served by staticfiles); only this
        # HTML entrypoint must always revalidate. ``no-cache`` =
        # "store but revalidate before use"; combined with the
        # per-user CSRF cookie + auth gate, the shell is per-request
        # anyway. (Also avoids the recurring "I still see the old
        # build" after an upgrade.)
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


class DarStaffAuthenticationForm(AuthenticationForm):
    """Login form that admits only **active staff** users.

    Mirrors ``django.contrib.admin.forms.AdminAuthenticationForm`` (the
    same ``is_active and is_staff`` gate) but does **not** import
    ``django.contrib.admin`` — so the package's own login keeps working
    even when the consumer has removed ``django.contrib.admin`` from
    ``INSTALLED_APPS`` (issue: "when the Django admin is off, the
    django-admin-react login replaces it").

    Rejecting non-staff at the form level (rather than letting login
    succeed then 403-ing at the SPA) avoids a redirect loop:
    login → SPA → not-authorized → login → …
    """

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "Please enter the correct username and password for a staff "
            "account. Note that both fields may be case-sensitive."
        ),
    }

    def confirm_login_allowed(self, user: Any) -> None:
        """Reject inactive or non-staff users with the generic message."""
        if not user.is_active or not user.is_staff:
            raise ValidationError(
                self.error_messages["invalid_login"],
                code="invalid_login",
            )


class DarLoginView(LoginView):
    """The package's own login page — Django's ``LoginView`` + a staff form.

    Reuses Django's session auth end-to-end (no parallel auth system,
    per ``SECURITY.md``): ``LoginView`` runs ``authenticate`` +
    ``login``, CSRF is enforced by Django's middleware on the POST, and
    the session cookie is the same one the rest of the package reads.

    Mounted at ``<mount>/login/`` (see ``urls.py``). ``_redirect_to_login``
    falls back to this when no admin / custom ``LOGIN_URL`` is available,
    so a consumer who turns the legacy admin off still gets a working,
    package-branded login.
    """

    template_name = "admin_react/login.html"
    authentication_form = DarStaffAuthenticationForm
    # NOT ``redirect_authenticated_user = True``: an authenticated but
    # non-staff user would be bounced login → SPA (which 403s non-staff
    # and redirects back to login) → login → … in an infinite loop.
    # Leaving it False makes the login page simply render for an
    # already-authenticated user, breaking the loop. (Proper
    # "you need staff access" messaging for that case is ACCEPTANCE
    # §2.3 O-5 — a separate SpaIndexView follow-up.)
    redirect_authenticated_user = False

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add the brand title so the login page matches the SPA shell."""
        context = super().get_context_data(**kwargs)
        context["brand_title"] = _resolve_brand_title(get_admin_site())
        context["brand_logo_url"] = dar_conf.BRAND_LOGO_URL
        return context


class DarLogoutView(LogoutView):
    """Logout endpoint that returns to the package's own login page.

    Mounted at ``<mount>/logout/``. ``next_page`` resolves lazily to the
    package login so logout works without the legacy admin.
    """

    # ``reverse_lazy`` returns a lazy str proxy (``_StrPromise``); the
    # base ``next_page`` is annotated ``str | None``. The proxy resolves
    # to a str at access time, so the cast is type-only.
    next_page = cast(str, reverse_lazy("django_admin_react:login"))


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

    # 3. The package's OWN login page. Always resolvable (it's in this
    #    package's urlpatterns), so it's the reliable fallback when the
    #    consumer has turned the legacy admin off — the django-admin-
    #    react login replaces the admin login automatically.
    if login_url is None:
        try:
            login_url = reverse("django_admin_react:login")
        except NoReverseMatch:
            login_url = None

    # 4. Stock admin login.
    if login_url is None:
        try:
            login_url = reverse("admin:login")
        except NoReverseMatch:
            login_url = "/accounts/login/"

    # Percent-encode the ``next`` value (``urlencode``) so a crafted
    # request path can't break out of the query parameter and rewrite
    # the redirect target. The redirect *target* (``login_url``) is
    # always a trusted, package-/settings-derived URL; ``next`` is
    # consumer-facing and re-validated by Django's login view via
    # ``url_has_allowed_host_and_scheme`` before any post-login bounce.
    # (Clears CodeQL ``py/url-redirection``.)
    next_param = urlencode({"next": request.get_full_path()})
    return redirect(f"{login_url}?{next_param}")
