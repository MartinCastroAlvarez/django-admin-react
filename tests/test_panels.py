"""Tests for the per-model panel endpoint (Issue #65).

Verifies the auth / opt-in / name-resolution / permission flow on
``GET …/<pk>/panel/<name>/``. The handler's own response shape is
opaque to the package — we only verify the envelope wrapping.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextlib import suppress

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import Client


@contextmanager
def admin_attr(model_cls, **values):
    model_admin = admin.site._registry[model_cls]
    sentinel = object()
    originals: dict = {}
    try:
        for name, value in values.items():
            originals[name] = model_admin.__dict__.get(name, sentinel)
            setattr(model_admin, name, value)
        yield
    finally:
        for name, original in originals.items():
            if original is sentinel:
                with suppress(AttributeError):
                    delattr(model_admin, name)
            else:
                setattr(model_admin, name, original)


def _panel_url(pk: int, name: str) -> str:
    return f"/admin-react/api/v1/auth/group/{pk}/panel/{name}/"


# --------------------------------------------------------------------------- #
# Default: ModelAdmin without panels → 404 on every panel URL                 #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_admin_without_panels_returns_404(superuser_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    response = superuser_client.get(_panel_url(g.pk, "anything"))
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Auth matrix                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_forbidden(anon_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    response = anon_client.get(_panel_url(g.pk, "x"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    response = user_client.get(_panel_url(g.pk, "x"))
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Happy path: registered panel returns the handler's data                     #
# --------------------------------------------------------------------------- #
def _audit_trail(self, request, obj):  # noqa: ARG001
    return {"entries": [{"at": "2025-10-05", "by": "system", "what": "created"}]}


@pytest.mark.django_db
def test_registered_panel_returns_handler_data(superuser_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    ma = admin.site._registry[Group]
    bound = _audit_trail.__get__(ma)
    with admin_attr(
        Group,
        panels={"audit_trail": "_audit_trail"},
        _audit_trail=bound,
    ):
        response = superuser_client.get(_panel_url(g.pk, "audit_trail"))
    assert response.status_code == 200
    body = response.json()
    assert body["panel"] == "audit_trail"
    assert body["data"] == {"entries": [{"at": "2025-10-05", "by": "system", "what": "created"}]}


@pytest.mark.django_db
def test_unknown_panel_name_returns_404(superuser_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    ma = admin.site._registry[Group]
    bound = _audit_trail.__get__(ma)
    with admin_attr(
        Group,
        panels={"audit_trail": "_audit_trail"},
        _audit_trail=bound,
    ):
        response = superuser_client.get(_panel_url(g.pk, "no_such_panel"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_panel_with_unresolvable_handler_returns_404(
    superuser_client: Client,
) -> None:
    """Panel name maps to a non-existent method → 404 (not 500)."""
    g = Group.objects.create(name="alpha")
    with admin_attr(
        Group,
        panels={"missing": "no_such_method_on_admin"},
    ):
        response = superuser_client.get(_panel_url(g.pk, "missing"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_pk_returns_404(superuser_client: Client) -> None:
    ma = admin.site._registry[Group]
    bound = _audit_trail.__get__(ma)
    with admin_attr(
        Group,
        panels={"audit_trail": "_audit_trail"},
        _audit_trail=bound,
    ):
        response = superuser_client.get(_panel_url(999999, "audit_trail"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_panel_response_has_no_store(superuser_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    ma = admin.site._registry[Group]
    bound = _audit_trail.__get__(ma)
    with admin_attr(
        Group,
        panels={"audit_trail": "_audit_trail"},
        _audit_trail=bound,
    ):
        response = superuser_client.get(_panel_url(g.pk, "audit_trail"))
    assert response["Cache-Control"] == "no-store"
