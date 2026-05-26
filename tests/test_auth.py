"""Security matrix for the React-login JSON endpoints.

``POST /api/v1/login/`` + ``POST /api/v1/logout/`` (``api/views/auth.py``).
Wire contract: ``docs/api-contract.md`` §7.

These endpoints are a thin JSON shell over Django's own
``authenticate`` / ``login`` / ``logout`` — the security properties
under test are exactly the ones the docstring of ``auth.py`` promises:

- CSRF enforced (no ``@csrf_exempt``).
- No username / permission enumeration — every failure mode returns
  the identical generic ``403 invalid_credentials``.
- The access policy (staff + active + ``AdminSite.has_permission``) is
  applied *before* a session is created — a valid-but-unauthorized user
  gets no session cookie.
- Logout is idempotent and CSRF-protected.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.test import Client

LOGIN_URL = "/admin-react/api/v1/login/"
LOGOUT_URL = "/admin-react/api/v1/logout/"

_GENERIC = {
    "error": {
        "code": "invalid_credentials",
        "message": "Invalid credentials or insufficient permissions.",
    }
}


# Auth-logic tests use the default client (CSRF not enforced) so the
# business logic is exercised without CSRF plumbing. CSRF enforcement
# itself is covered by the two dedicated tests below using
# ``enforce_csrf_checks=True``. This is Django's standard split: test
# the gate separately from the logic it gates.
def _client() -> Client:
    """Default test client (CSRF not enforced — see module note)."""
    return Client()


# --------------------------------------------------------------------------- #
# CSRF — enforced, no exemption                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_login_without_csrf_is_403() -> None:
    """A login POST with no CSRF token is rejected by middleware."""
    client = Client(enforce_csrf_checks=True)
    User.objects.create_user("alice", password="pw-correct-1", is_staff=True)
    response = client.post(
        LOGIN_URL,
        data=json.dumps({"username": "alice", "password": "pw-correct-1"}),
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_logout_without_csrf_is_403() -> None:
    """A logout POST with no CSRF token is rejected (no forged logout)."""
    client = Client(enforce_csrf_checks=True)
    response = client.post(LOGOUT_URL)
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Successful login                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_staff_login_succeeds_and_sets_session() -> None:
    """Active staff with the right password gets 200 + a session."""
    User.objects.create_user("alice", password="pw-correct-1", is_staff=True)
    client = _client()
    response = client.post(
        LOGIN_URL,
        data=json.dumps({"username": "alice", "password": "pw-correct-1"}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["user"]["username"] == "alice"
    assert body["user"]["is_staff"] is True
    assert client.session.get("_auth_user_id")
    # Auth result must never be cached.
    assert response["Cache-Control"] == "no-store"


# --------------------------------------------------------------------------- #
# No enumeration — every failure mode looks identical                         #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_unknown_user_returns_generic_403() -> None:
    response = _client().post(
        LOGIN_URL,
        data=json.dumps({"username": "ghost", "password": "whatever-1"}),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json() == _GENERIC


@pytest.mark.django_db
def test_wrong_password_returns_generic_403() -> None:
    User.objects.create_user("alice", password="pw-correct-1", is_staff=True)
    response = _client().post(
        LOGIN_URL,
        data=json.dumps({"username": "alice", "password": "pw-WRONG"}),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json() == _GENERIC


@pytest.mark.django_db
def test_inactive_user_returns_generic_403_no_session() -> None:
    u = User.objects.create_user("alice", password="pw-correct-1", is_staff=True)
    u.is_active = False
    u.save()
    client = _client()
    response = client.post(
        LOGIN_URL,
        data=json.dumps({"username": "alice", "password": "pw-correct-1"}),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json() == _GENERIC
    assert not client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_valid_nonstaff_user_returns_generic_403_no_session() -> None:
    """Correct password but not staff → same generic 403, NO session.

    This is the load-bearing access-policy test: a valid-but-unauthorized
    user must not receive a session, and the response must be
    indistinguishable from a wrong password (no permission oracle).
    """
    User.objects.create_user("bob", password="pw-correct-1", is_staff=False)
    client = _client()
    response = client.post(
        LOGIN_URL,
        data=json.dumps({"username": "bob", "password": "pw-correct-1"}),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json() == _GENERIC
    # The critical assertion: no session was established for the
    # valid-but-unauthorized user.
    assert not client.session.get("_auth_user_id")


# --------------------------------------------------------------------------- #
# Malformed input                                                             #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_malformed_json_is_400() -> None:
    response = _client().post(
        LOGIN_URL,
        data="not json{",
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_missing_fields_returns_generic_403() -> None:
    response = _client().post(
        LOGIN_URL,
        data=json.dumps({"username": "alice"}),  # no password
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json() == _GENERIC


# --------------------------------------------------------------------------- #
# Logout                                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_logout_flushes_session() -> None:
    User.objects.create_user("alice", password="pw-correct-1", is_staff=True)
    client = _client()
    client.post(
        LOGIN_URL,
        data=json.dumps({"username": "alice", "password": "pw-correct-1"}),
        content_type="application/json",
    )
    assert client.session.get("_auth_user_id")
    response = client.post(LOGOUT_URL)
    assert response.status_code == 200
    assert not client.session.get("_auth_user_id")
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_logout_while_anonymous_is_noop_200() -> None:
    """Logout with no session is a harmless 200 (idempotent)."""
    response = _client().post(LOGOUT_URL)
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# GET is not allowed                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_login_get_not_allowed() -> None:
    client = Client()
    response = client.get(LOGIN_URL)
    assert response.status_code == 405


@pytest.mark.django_db
def test_reserved_login_label_does_not_route_to_a_model() -> None:
    """A consumer model under app_label 'login' must 404, not shadow.

    ``login`` / ``logout`` are in ``RESERVED_APP_LABELS`` so the literal
    auth routes can never be masked by a per-model route.
    """
    from django_admin_react.api.registry import RESERVED_APP_LABELS

    assert "login" in RESERVED_APP_LABELS
    assert "logout" in RESERVED_APP_LABELS
