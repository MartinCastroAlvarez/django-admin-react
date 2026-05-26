"""Tests for ``GET /api/v1/<app>/<model>/<pk>/delete-preview/`` (#153).

The endpoint mirrors the legacy admin's delete-confirmation interstitial:
cascade counts, protected objects, perms-needed, and a ``can_delete``
verdict — without performing the delete.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from tests.helpers import admin_override

COLLECTION_URL = "/admin-react/api/v1/auth/group/"


def _url(pk: int) -> str:
    return f"{COLLECTION_URL}{pk}/delete-preview/"


@pytest.mark.django_db
def test_anonymous_unauthorized(anon_client: Client) -> None:
    g = Group.objects.create(name="g")
    assert anon_client.get(_url(g.pk)).status_code in (302, 403)


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    g = Group.objects.create(name="g")
    assert user_client.get(_url(g.pk)).status_code == 403


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    assert (
        superuser_client.get("/admin-react/api/v1/auth/nope/1/delete-preview/").status_code == 404
    )


@pytest.mark.django_db
def test_bogus_pk_not_found(superuser_client: Client) -> None:
    assert superuser_client.get(_url(999999)).status_code == 404


@pytest.mark.django_db
def test_without_delete_permission_forbidden(superuser_client: Client) -> None:
    g = Group.objects.create(name="g")
    with admin_override(Group, has_delete_permission=lambda self, request, obj=None: False):
        assert superuser_client.get(_url(g.pk)).status_code == 403


@pytest.mark.django_db
def test_preview_shape_for_leaf_object(superuser_client: Client) -> None:
    g = Group.objects.create(name="leaf")
    response = superuser_client.get(_url(g.pk))
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == {"pk": g.pk, "label": "leaf"}
    assert isinstance(body["cascade"], list)
    # The object's own model appears in the cascade count.
    assert any("group" in c["model"].lower() for c in body["cascade"])
    assert body["protected"] == []
    assert body["perms_needed"] == []
    assert body["can_delete"] is True
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_preview_does_not_delete(superuser_client: Client) -> None:
    g = Group.objects.create(name="survivor")
    superuser_client.get(_url(g.pk))
    # Preview is read-only — the object must still exist.
    assert Group.objects.filter(pk=g.pk).exists()
