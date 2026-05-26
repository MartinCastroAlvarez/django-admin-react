"""Permission helpers.

The package's default permission gate is:

    user.is_authenticated and user.is_active and user.is_staff
    and admin_site.has_permission(request)

Per-operation gates always go through the relevant
``ModelAdmin.has_*_permission(request, obj=None)`` method.

403 responses come in two flavours so the SPA can distinguish "you were
never authenticated" from "your session expired" (Issue #63):

- ``error.code = "forbidden"`` — generic permission denial; the SPA
  redirects to the configured login URL.
- ``error.code = "session_expired"`` — the request carried a session
  cookie but the resolved user is anonymous; the SPA shows a re-login
  modal that returns the user to the same page after sign-in.

See ``SECURITY.md`` §3 (rules 1 and 12) for the contract this enforces
and ``docs/api-contract.md`` §6 for the wire shape.
"""

from __future__ import annotations

from typing import Final

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse

from django_admin_react.api.registry import get_admin_site


def _user_is_active_staff(request: HttpRequest) -> bool:
    """Return True iff the request user is authenticated, active, and staff.

    The triple check is intentional and each part is load-bearing.

    - ``is_authenticated`` rejects ``AnonymousUser``.
    - ``is_active`` ensures a deactivated account loses access immediately;
      relying on ``is_staff`` alone would still let a disabled superuser
      through.
    - ``is_staff`` is the standard Django admin gate.

    ``getattr(user, "is_active", False)`` (rather than ``user.is_active``)
    is defensive: a custom user model might omit the attribute, and the
    safe default is "no".
    """
    user = getattr(request, "user", None)
    return bool(
        user is not None
        and user.is_authenticated
        and getattr(user, "is_active", False)
        and getattr(user, "is_staff", False)
    )


def is_admin_user(request: HttpRequest, admin_site: AdminSite | None = None) -> bool:
    """Return True iff the request may access the package's API.

    The package's default policy is staff-only (rule 1 in ``SECURITY.md``
    §3). ``AdminSite.has_permission`` is the consumer's escape hatch: if
    a consumer's custom site allows non-staff users to access the admin,
    this package follows that decision (`ARCHITECTURE.md` §4.2).
    """
    if not _user_is_active_staff(request):
        return False
    site = admin_site if admin_site is not None else get_admin_site()
    return bool(site.has_permission(request))


_FORBIDDEN_BODY: Final[dict[str, dict[str, str]]] = {
    "error": {"code": "forbidden", "message": "You do not have permission."}
}

_SESSION_EXPIRED_BODY: Final[dict[str, dict[str, str]]] = {
    "error": {
        "code": "session_expired",
        "message": "Your session has expired. Please sign in again.",
    }
}


def is_session_expired(request: HttpRequest) -> bool:
    """Detect "had a session cookie, but the user is now anonymous".

    The signal is conservative on purpose: we only flag expiry when
    the request carried a non-empty session cookie *and* the user
    resolved to anonymous (no ``is_authenticated``). Without that
    cookie there's nothing to expire — the user is just not signed
    in (the canonical anonymous case the contract has always handled).

    The check is read-only and never touches the session backend;
    it inspects the cookie name in ``settings.SESSION_COOKIE_NAME``
    and the resolved ``request.user`` only. Defensive fallback to
    ``False`` if any attribute is missing — the worst case is the
    SPA gets the generic ``"forbidden"`` envelope and falls back to
    its normal login-redirect path.
    """
    cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
    cookie_value = request.COOKIES.get(cookie_name)
    if not cookie_value:
        return False
    user = getattr(request, "user", None)
    return bool(user is None or not getattr(user, "is_authenticated", False))


def forbidden_response(request: HttpRequest | None = None) -> HttpResponse:
    """Return the package's canonical 403 envelope.

    When ``request`` is provided and ``is_session_expired(request)``
    returns ``True`` (the request carried a session cookie but the
    user is anonymous), the body uses the ``session_expired`` error
    code so the SPA can render a re-login modal instead of a hard
    redirect. Without the argument, or when no expiry signal is
    detected, the body is the generic ``forbidden`` envelope.

    The body never includes data identifying the resource (per
    ``SECURITY.md`` §3 rule 12). For unauthenticated requests, callers
    may also want to redirect to ``settings.LOGIN_URL`` — that's a
    caller-level choice and not encoded here.
    """
    body = _FORBIDDEN_BODY
    if request is not None and is_session_expired(request):
        body = _SESSION_EXPIRED_BODY
    response = JsonResponse(body, status=403)
    # Discourage caching of a permission decision.
    response["Cache-Control"] = "no-store"
    return response
