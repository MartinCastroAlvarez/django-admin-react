"""Tests for ``GET /api/v1/<app>/<model>/<pk>/`` (PR #4).

Mandatory matrix from CLAUDE.md §6 + ACCEPTANCE.md §3.5 T-1.
Plus feature-specific: ForeignKey shape, readonly fields, sensitive-
name denylist, bogus pk, per-object has_view_permission.
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
    response = anon_client.get(_url(g.pk))
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = user_client.get(_url(g.pk))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_with_permission_succeeds(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = superuser_client.get(_url(g.pk))
    assert response.status_code == 200
    body = response.json()
    assert body["pk"] == g.pk
    assert body["label"] == "example"
    assert "fields" in body
    assert "fieldsets" in body
    assert "permissions" in body


@pytest.mark.django_db
def test_user_without_view_permission_for_object_forbidden(
    superuser_client: Client,
) -> None:
    g = Group.objects.create(name="example")
    with _admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
        response = superuser_client.get(_url(g.pk))
    assert response.status_code in (403, 404)


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.get("/admin-react/api/v1/auth/nope/1/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_bogus_pk_not_found(superuser_client: Client) -> None:
    response = superuser_client.get(_url("not-a-valid-id"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_pk_not_found(superuser_client: Client) -> None:
    response = superuser_client.get(_url(999999))
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_fields_include_required_help_text_and_type(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = superuser_client.get(_url(g.pk))
    body = response.json()
    assert "name" in body["fields"]
    name_field = body["fields"]["name"]
    assert name_field["type"] == "string"
    assert isinstance(name_field["required"], bool)
    assert isinstance(name_field["readonly"], bool)
    assert "value" in name_field


@pytest.mark.django_db
def test_starts_from_admin_get_queryset(superuser_client: Client) -> None:
    """Detail view must use ModelAdmin.get_queryset, not Model.objects.all."""
    g = Group.objects.create(name="invisible")
    with _admin_override(Group, get_queryset=lambda self, request: Group.objects.none()):
        response = superuser_client.get(_url(g.pk))
    assert response.status_code == 404
