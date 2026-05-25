"""Shared pytest fixtures for the django-admin-react test suite.

These fixtures provide users at the three permission levels the security
contract distinguishes:

- ``anon_client``     — no session.
- ``user_client``     — logged in, ``is_active=True``, ``is_staff=False``.
- ``staff_client``    — logged in, ``is_active=True``, ``is_staff=True``,
                        without superuser privileges.
- ``superuser_client``— logged in, superuser (used sparingly; most tests
                        should pin behavior to a specific permission).

Tests that rely on ``ModelAdmin`` permissions should override the
relevant ``has_*_permission`` on a per-test basis rather than swapping
users — the user identity is not the contract; the admin's answer is.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


@pytest.fixture
def anon_client() -> Client:
    return Client()


@pytest.fixture
def user_client(db) -> Client:  # noqa: ARG001 — db fixture forces DB setup
    User = get_user_model()
    user = User.objects.create_user(
        username="non_staff",
        password="test-only-non-staff",  # noqa: S106
        email="non_staff@example.com",
        is_staff=False,
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def staff_client(db) -> Client:  # noqa: ARG001
    User = get_user_model()
    user = User.objects.create_user(
        username="staff",
        password="test-only-staff",  # noqa: S106
        email="staff@example.com",
        is_staff=True,
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def superuser_client(db) -> Client:  # noqa: ARG001
    User = get_user_model()
    user = User.objects.create_superuser(
        username="root",
        password="test-only-root",  # noqa: S106
        email="root@example.com",
    )
    client = Client()
    client.force_login(user)
    return client
