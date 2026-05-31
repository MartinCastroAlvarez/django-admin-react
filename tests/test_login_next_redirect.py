"""Lock the ``?next=`` open-redirect protection on ``DarLoginView`` (#636).

``DarLoginView`` subclasses ``django.contrib.auth.views.LoginView``,
which defaults ``success_url_allowed_hosts = set()`` and rejects any
``next`` query value that points off-host. The risk: a subclass that
overrides ``get_success_url`` / ``form_valid`` without preserving the
allow-list check would silently re-introduce an open redirect — every
"please log in, then return to <X>" mail-out would become a phishing
weapon.

This test posts a login with ``?next=https://evil.example.com/`` and
asserts the post-login redirect target is NOT off-host. If a future
change overrides the redirect helpers without the safe-host gate,
this test fails red and the regression doesn't ship.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

LOGIN_URL = "/admin-react/login/"


@pytest.fixture
def staff_user(db):
    u = get_user_model().objects.create_user(username="alice", password="pw12345!")
    u.is_staff = True
    u.is_active = True
    u.save()
    return u


def test_next_param_rejects_external_host(staff_user):
    """An off-host ``next`` value MUST NOT survive into the redirect target."""
    c = Client()
    response = c.post(
        f"{LOGIN_URL}?next=https://evil.example.com/phish",
        data={"username": "alice", "password": "pw12345!"},
    )
    # Successful login should redirect to the safe default, not off-host.
    assert response.status_code == 302, "Login POST should 302 on success."
    target = response.headers["Location"]
    parsed = urlparse(target)
    # An empty netloc means same-host (a path-only redirect like `/admin/`).
    # Any non-empty netloc must NOT be the attacker's host.
    assert parsed.netloc in ("", "testserver"), (
        f"Login redirected to off-host URL {target!r} — open redirect."
    )


def test_next_param_accepts_same_host_path(staff_user):
    """A same-host ``next`` path IS honoured (the legitimate use case)."""
    c = Client()
    response = c.post(
        f"{LOGIN_URL}?next=/admin-react/auth/user/",
        data={"username": "alice", "password": "pw12345!"},
    )
    assert response.status_code == 302
    target = response.headers["Location"]
    parsed = urlparse(target)
    assert parsed.netloc in ("", "testserver")
    assert parsed.path == "/admin-react/auth/user/"
