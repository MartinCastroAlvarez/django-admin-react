"""Tests for the package's own login / logout (replaces admin login).

Requirement: "once I turn the django admin off, the login page of the
django-admin-react should replace it." The package mounts its own
``login/`` (Django ``LoginView`` + a staff-only form) and
``SpaIndexView`` falls back to it when no admin login is reachable.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.test import override_settings
from django.urls import reverse

LOGIN_URL = "/admin-react/login/"
LOGOUT_URL = "/admin-react/logout/"
SPA_URL = "/admin-react/"


@pytest.fixture
def make_user(db):
    def _make(username: str, *, staff: bool, active: bool = True, password: str = "pw12345!"):
        u = get_user_model().objects.create_user(username=username, password=password)
        u.is_staff = staff
        u.is_active = active
        u.save()
        return u

    return _make


# --------------------------------------------------------------------------- #
# The login page itself                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_login_url_reverses_in_package_namespace() -> None:
    assert reverse("django_admin_react:login") == LOGIN_URL


@pytest.mark.django_db
def test_login_page_renders(client: Client) -> None:
    response = client.get(LOGIN_URL)
    assert response.status_code == 200
    body = response.content.decode()
    assert 'name="username"' in body
    assert 'name="password"' in body
    assert "csrfmiddlewaretoken" in body


@pytest.mark.django_db
def test_staff_can_log_in(client: Client, make_user) -> None:
    make_user("boss", staff=True)
    response = client.post(LOGIN_URL, {"username": "boss", "password": "pw12345!"})
    assert response.status_code == 302
    # Session is now authenticated — the SPA renders instead of redirecting.
    spa = client.get(SPA_URL)
    assert spa.status_code == 200


@pytest.mark.django_db
def test_non_staff_rejected_at_login(client: Client, make_user) -> None:
    make_user("peon", staff=False)
    response = client.post(LOGIN_URL, {"username": "peon", "password": "pw12345!"})
    # Re-renders the form with an error; never establishes a staff session.
    assert response.status_code == 200
    assert "staff account" in response.content.decode().lower()
    # The SPA still bounces them.
    assert client.get(SPA_URL).status_code in (302,)


@pytest.mark.django_db
def test_bad_password_rejected(client: Client, make_user) -> None:
    make_user("boss", staff=True)
    response = client.post(LOGIN_URL, {"username": "boss", "password": "wrong"})
    assert response.status_code == 200
    assert client.get(SPA_URL).status_code == 302


@pytest.mark.django_db
def test_next_param_round_trips(client: Client, make_user) -> None:
    make_user("boss", staff=True)
    target = "/admin-react/auth/group/"
    response = client.post(
        f"{LOGIN_URL}?next={target}",
        {"username": "boss", "password": "pw12345!", "next": target},
    )
    assert response.status_code == 302
    assert response["Location"] == target


@pytest.mark.django_db
def test_logout_returns_to_login(client: Client, make_user) -> None:
    make_user("boss", staff=True)
    client.post(LOGIN_URL, {"username": "boss", "password": "pw12345!"})
    response = client.post(LOGOUT_URL)
    assert response.status_code == 302
    assert response["Location"] == LOGIN_URL
    # Session cleared — SPA bounces again.
    assert client.get(SPA_URL).status_code == 302


# --------------------------------------------------------------------------- #
# Fallback when the legacy admin is OFF                                        #
# --------------------------------------------------------------------------- #
@override_settings(ROOT_URLCONF="tests.test_project.urls_no_admin", LOGIN_URL="/accounts/login/")
@pytest.mark.django_db
def test_spa_falls_back_to_package_login_when_admin_off(client: Client) -> None:
    # No admin mounted + LOGIN_URL is Django's untouched default → the
    # package login must be the redirect target.
    response = client.get(SPA_URL)
    assert response.status_code == 302
    assert response["Location"].startswith(LOGIN_URL)
    assert "next=" in response["Location"]
