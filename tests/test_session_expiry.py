"""Tests for the session-expiry contract (Issue #63).

Wire contract: ``docs/api-contract.md`` §6 — the SPA distinguishes
"had a session, now anonymous" from "never had a session" so it can
render a re-login modal instead of a hard redirect.

Covered:

- Anonymous request with **no** session cookie → ``forbidden``.
- Anonymous request **with** a session cookie → ``session_expired``.
- Authenticated non-staff (with a real session) → ``forbidden``
  (not expiry; the user IS authenticated, just not permitted).
- The helper ``is_session_expired`` returns the right boolean for
  each case.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import Client

from django_admin_react.api.permissions import is_session_expired

REGISTRY_URL = "/admin-react/api/v1/registry/"


# --------------------------------------------------------------------------- #
# is_session_expired helper                                                   #
# --------------------------------------------------------------------------- #
def test_is_session_expired_no_cookie() -> None:
    """No session cookie → not expired (just anonymous)."""
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    assert is_session_expired(request) is False


def test_is_session_expired_with_cookie_anonymous_user() -> None:
    """Session cookie present + anonymous user → expired."""
    from django.contrib.auth.models import AnonymousUser
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.COOKIES[settings.SESSION_COOKIE_NAME] = "stale-session-id"
    request.user = AnonymousUser()
    assert is_session_expired(request) is True


def test_is_session_expired_with_cookie_authenticated_user(db) -> None:  # noqa: ARG001
    """Session cookie present + authenticated user → not expired (signed in)."""
    from django.contrib.auth import get_user_model
    from django.test import RequestFactory

    user = get_user_model().objects.create_user(
        username="x",
        password="y",  # noqa: S106
        is_staff=False,
    )
    request = RequestFactory().get("/")
    request.COOKIES[settings.SESSION_COOKIE_NAME] = "real-session-id"
    request.user = user
    assert is_session_expired(request) is False


# --------------------------------------------------------------------------- #
# Wire shape on the registry endpoint                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_no_session_returns_generic_forbidden(anon_client: Client) -> None:
    """No session cookie → ``error.code = "forbidden"``."""
    response = anon_client.get(REGISTRY_URL)
    # Either 302 redirect (the framework's anonymous path) or 403 JSON.
    # The registry view returns 403 with the JSON envelope.
    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "forbidden", "message": "You do not have permission."}
    }


@pytest.mark.django_db
def test_anonymous_with_stale_session_cookie_returns_session_expired(
    anon_client: Client,
) -> None:
    """Anonymous + session cookie → ``error.code = "session_expired"``.

    Simulates the real-world case where the user was signed in, the
    server-side session was invalidated (manual logout from another
    device, session expiry, or a security-driven flush), but the
    browser still holds the cookie from the previous session.
    """
    anon_client.cookies[settings.SESSION_COOKIE_NAME] = "stale-session-id"
    response = anon_client.get(REGISTRY_URL)
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "session_expired"
    assert "expired" in body["error"]["message"].lower()
    # Cache header still no-store (Rule 12 preserved).
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_authenticated_non_staff_returns_forbidden_not_expiry(
    user_client: Client,
) -> None:
    """Logged-in non-staff is forbidden, not expired (they ARE signed in)."""
    response = user_client.get(REGISTRY_URL)
    assert response.status_code == 403
    # NOT session_expired — the user is actually signed in; they
    # just don't have staff permissions.
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.django_db
def test_session_expiry_envelope_on_list_endpoint(anon_client: Client) -> None:
    """The contract applies to every endpoint, not only registry."""
    anon_client.cookies[settings.SESSION_COOKIE_NAME] = "stale-session-id"
    response = anon_client.get("/admin-react/api/v1/auth/group/")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "session_expired"
