"""``POST /api/v1/login/`` + ``POST /api/v1/logout/`` — React-driven auth.

Wire contract: ``docs/api-contract.md`` §7 (authentication endpoints).

These endpoints let the SPA render its **own** login form instead of
redirecting to Django's HTML login page. They do **not** invent an auth
mechanism — they are a thin JSON shell over Django's own
``authenticate`` / ``login`` / ``logout``. The session cookie, the
password hashing, the user model, and the access policy are all
Django's. (`ARCHITECTURE.md` §4.2, `SECURITY.md` §3.)

These are the secure server-side primitive a React login form POSTs to.
The complementary piece — serving the SPA shell (and its CSRF cookie) to
*anonymous* users so the React form can render before authentication —
lives in ``SpaIndexView`` and is wired separately; until that lands, the
endpoints are reachable directly by any client that already holds a CSRF
token (e.g. the existing authenticated shell, or the server-rendered
``<mount>/login/`` page). The auth *mechanism* is identical either way;
only the UI differs.

Security properties (each is load-bearing — see the test matrix in
``tests/test_auth.py``):

- **CSRF is enforced.** Neither view is ``@csrf_exempt``; Django's
  ``CsrfViewMiddleware`` runs. The shell (served to anonymous users
  when ``REACT_LOGIN`` is on) sets the CSRF cookie via
  ``get_token``, and the SPA echoes it as ``X-CSRFToken`` on the
  login/logout POST. A login POST without a valid CSRF token is a
  ``403`` from the middleware before this code runs.
- **No username / permission enumeration.** "no such user", "wrong
  password", "inactive account", and "valid creds but not staff" all
  return the *identical* ``403 invalid_credentials`` body. Django's
  ``ModelBackend.authenticate`` runs the password hasher even when the
  username doesn't exist (its dummy-hash run), so response timing does
  not leak username existence either.
- **The access policy is applied before any session is created.** We
  set ``request.user`` to the authenticated candidate and run the same
  ``is_admin_user`` gate the rest of the API uses (staff + active +
  ``AdminSite.has_permission``). Only when it passes do we call
  ``login()`` — so a valid-but-unauthorized user never gets a session
  cookie, not even briefly.
- **Session-fixation defense.** ``django.contrib.auth.login`` rotates
  the session key on a successful login (Django's built-in behavior);
  a pre-login session id cannot be reused post-login.
- **The password is never logged or echoed.** It is read from the JSON
  body, passed straight to ``authenticate``, and never stored,
  formatted into a message, or returned.
- **``Cache-Control: no-store``** on every response so an intermediary
  never caches the auth result.

Out of scope (documented in ``SECURITY.md`` §2): rate limiting /
brute-force throttling on login. That remains the consumer's job — the
package never replaces Django's login *mechanism*, only its *UI*. A
recommended ``django-ratelimit`` / ``django-axes`` integration is noted
in ``SECURITY.md`` (QSEC-2026-05-25-01).
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site

# A single generic rejection for every failure mode of the login
# endpoint. Using one message for "no such user", "wrong password",
# "inactive", and "not staff" is what makes the endpoint a non-oracle:
# an attacker learns only "those credentials did not grant access",
# never *which* of the four reasons applied.
_INVALID_CODE = "invalid_credentials"
_INVALID_MESSAGE = "Invalid credentials or insufficient permissions."


def _no_store(response: HttpResponse) -> HttpResponse:
    """Stamp ``Cache-Control: no-store`` — auth results must never cache."""
    response["Cache-Control"] = "no-store"
    return response


def _error(code: str, message: str, status: int) -> HttpResponse:
    """Build the standard ``{"error": {...}}`` envelope with no-store."""
    return _no_store(JsonResponse({"error": {"code": code, "message": message}}, status=status))


def _invalid_credentials() -> HttpResponse:
    """The single generic credentials-rejected response (HTTP 403)."""
    return _error(_INVALID_CODE, _INVALID_MESSAGE, 403)


def _user_payload(user: Any) -> dict[str, Any]:
    """Minimal post-login user block — the same shape the registry uses.

    Exposes only what the signed-in user already knows about themselves:
    pk, username, display name, ``is_staff``, ``is_superuser``. No email,
    no group memberships, no permission codenames.
    """
    full_name = (user.get_full_name() or "").strip() if hasattr(user, "get_full_name") else ""
    return {
        "id": user.pk,
        "username": user.get_username(),
        "is_staff": bool(getattr(user, "is_staff", False)),
        "is_superuser": bool(getattr(user, "is_superuser", False)),
        "display_name": full_name or user.get_username(),
    }


class LoginView(View):
    """``POST /api/v1/login/`` — establish a session from credentials.

    Body: ``{"username": "...", "password": "..."}``. On success returns
    ``200`` with ``{"user": {...}}`` and a rotated session cookie. On any
    failure returns the generic ``403 invalid_credentials`` (no oracle).
    """

    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Authenticate, apply the access policy, then establish a session.

        Order is deliberate: the access-policy gate runs **before**
        ``login()``, so a valid-but-unauthorized user (e.g. correct
        password but ``is_staff`` is False) never receives a session
        cookie. CSRF is enforced by middleware before this method runs.
        """
        try:
            payload = json.loads(request.body or b"{}")
        except (ValueError, TypeError):
            return _error("bad_request", "Malformed JSON body.", 400)
        if not isinstance(payload, dict):
            return _error("bad_request", "Malformed JSON body.", 400)

        username = payload.get("username")
        password = payload.get("password")
        # A non-string username/password is a malformed credential, not a
        # server error — collapse it into the same generic rejection so
        # the shape of the failure never varies.
        if not isinstance(username, str) or not isinstance(password, str):
            return _invalid_credentials()

        # ``authenticate`` returns ``None`` for an unknown username, a
        # wrong password, OR an inactive user (ModelBackend rejects
        # ``is_active=False`` via ``user_can_authenticate``). All three
        # collapse into the same branch.
        user = authenticate(request, username=username, password=password)
        if user is None:
            return _invalid_credentials()

        # Apply the package's access policy BEFORE creating a session.
        # ``is_admin_user`` reads ``request.user``; set the candidate so
        # the staff + ``AdminSite.has_permission`` check sees it. No
        # session has been created yet, so a rejected user leaves with
        # nothing.
        request.user = user
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return _invalid_credentials()

        # Policy passed — establish the session. ``login()`` rotates the
        # session key (session-fixation defense) and writes the auth
        # cookie via Django's session middleware.
        auth_login(request, user)
        return _no_store(JsonResponse({"user": _user_payload(user)}, status=200))


class LogoutView(View):
    """``POST /api/v1/logout/`` — flush the current session.

    Idempotent: a logout while already anonymous is a harmless ``200``
    no-op. CSRF is enforced (POST is unsafe), so a cross-site forged
    logout cannot drop a victim's session.
    """

    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """End the session via Django's ``logout`` and confirm with 200.

        ``logout()`` flushes the session and resets ``request.user`` to
        ``AnonymousUser`` regardless of prior auth state, so this never
        raises and never leaks whether a session existed.
        """
        auth_logout(request)
        return _no_store(JsonResponse({"detail": "logged out"}, status=200))
