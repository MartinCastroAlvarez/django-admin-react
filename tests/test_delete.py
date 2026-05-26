"""Tests for ``DELETE /api/v1/<app>/<model>/<pk>/`` (PR #5).

Mandatory matrix from ``CLAUDE.md`` §6 + ``ACCEPTANCE.md`` §3.5 T-1.
Plus feature-specific: ``ModelAdmin.delete_model`` is called (never
``obj.delete()``), no body on 204, 404 on bogus pk.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import Client


def _url(pk: object) -> str:
    return f"/admin-react/api/v1/auth/group/{pk}/"


@contextmanager
def _admin_override(model_cls, **method_returns) -> Iterator[None]:
    model_admin = admin.site._registry[model_cls]
    originals = {}
    try:
        for name, fn in method_returns.items():
            originals[name] = getattr(model_admin, name)
            setattr(model_admin, name, fn.__get__(model_admin))
        yield
    finally:
        for name, original in originals.items():
            setattr(model_admin, name, original)


# --------------------------------------------------------------------------- #
# Mandatory 8-row matrix                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_unauthorized(anon_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = anon_client.delete(_url(g.pk))
    assert response.status_code in (302, 403)
    assert Group.objects.filter(pk=g.pk).exists()


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = user_client.delete(_url(g.pk))
    assert response.status_code == 403
    assert Group.objects.filter(pk=g.pk).exists()


@pytest.mark.django_db
def test_superuser_can_delete(superuser_client: Client) -> None:
    g = Group.objects.create(name="goodbye")
    response = superuser_client.delete(_url(g.pk))
    assert response.status_code == 204
    assert response.content == b""
    assert not Group.objects.filter(pk=g.pk).exists()


@pytest.mark.django_db
def test_user_without_delete_permission_forbidden(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    with _admin_override(Group, has_delete_permission=lambda self, request, obj=None: False):
        response = superuser_client.delete(_url(g.pk))
    assert response.status_code == 403
    assert Group.objects.filter(pk=g.pk).exists()


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.delete("/admin-react/api/v1/auth/nope/1/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_pk_not_found(superuser_client: Client) -> None:
    response = superuser_client.delete(_url(999999))
    assert response.status_code == 404


@pytest.mark.django_db
def test_bogus_pk_not_found(superuser_client: Client) -> None:
    response = superuser_client.delete(_url("not-an-int"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_csrf_missing_on_unsafe_method_forbidden() -> None:
    from django.contrib.auth import get_user_model

    g = Group.objects.create(name="example")
    User = get_user_model()
    user = User.objects.create_superuser(
        username="csrf_root_delete",
        password="test-only-csrf-root-delete",  # noqa: S106
        email="csrf-delete@example.com",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.delete(_url(g.pk))
    assert response.status_code == 403
    assert Group.objects.filter(pk=g.pk).exists()


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_delete_model_is_called_not_obj_delete(superuser_client: Client) -> None:
    """Confirm deletes flow through ModelAdmin.delete_model (B-4)."""
    g = Group.objects.create(name="example")
    calls = []

    def fake_delete_model(self, request, obj):  # noqa: ARG001
        calls.append(obj.pk)
        obj.delete()

    with _admin_override(Group, delete_model=fake_delete_model):
        response = superuser_client.delete(_url(g.pk))
    assert response.status_code == 204
    assert calls == [g.pk]
    assert not Group.objects.filter(pk=g.pk).exists()


@pytest.mark.django_db
def test_starts_from_admin_get_queryset(superuser_client: Client) -> None:
    g = Group.objects.create(name="invisible")
    with _admin_override(Group, get_queryset=lambda self, request: Group.objects.none()):
        response = superuser_client.delete(_url(g.pk))
    assert response.status_code == 404
    assert Group.objects.filter(pk=g.pk).exists()
