"""Tests for ``PATCH /api/v1/<app>/<model>/<pk>/`` (PR #5).

Mandatory matrix from ``CLAUDE.md`` §6 + ``ACCEPTANCE.md`` §3.5 T-1.
Plus feature-specific: readonly rejection, partial-update merge, 404 on
bogus pk, save_model called with change=True.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.test import Client

from tests.helpers import admin_override


def _url(pk: object) -> str:
    return f"/admin-react/api/v1/auth/group/{pk}/"


def _patch(client: Client, pk: object, body: dict):
    return client.patch(_url(pk), data=json.dumps(body), content_type="application/json")


@pytest.mark.django_db
def test_db_integrity_error_returns_clean_409(superuser_client: Client) -> None:
    """A DB IntegrityError at save (constraint the form didn't catch / race)
    returns a clean 409 conflict envelope — not an uncaught 500 — and leaves
    the row unchanged (#404)."""
    g = Group.objects.create(name="orig")

    def raise_integrity(self, request, obj, form, change):  # noqa: ANN001
        raise IntegrityError("simulated unique violation")

    with admin_override(Group, save_model=raise_integrity):
        response = _patch(superuser_client, g.pk, {"name": "new"})
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "conflict"
    g.refresh_from_db()
    assert g.name == "orig"  # rolled back


# --------------------------------------------------------------------------- #
# Mandatory 8-row matrix                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_unauthorized(anon_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = anon_client.patch(
        _url(g.pk), data=json.dumps({"name": "x"}), content_type="application/json"
    )
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = _patch(user_client, g.pk, {"name": "x"})
    assert response.status_code == 403


@pytest.mark.django_db
def test_superuser_can_patch(superuser_client: Client) -> None:
    g = Group.objects.create(name="old")
    response = _patch(superuser_client, g.pk, {"name": "new"})
    assert response.status_code == 200
    g.refresh_from_db()
    assert g.name == "new"
    body = response.json()
    assert body["pk"] == g.pk
    assert body["label"] == "new"


@pytest.mark.django_db
def test_update_routes_writes_through_save_related(superuser_client: Client) -> None:
    """A consumer's ``save_related`` override is honoured on update (#402,
    Rule 1). Before the fix, update called ``form.save_m2m()`` directly and
    a consumer override was silently skipped."""
    g = Group.objects.create(name="old")
    calls = []

    def fake_save_related(self, request, form, formsets, change):  # noqa: ARG001
        calls.append(change)
        form.save_m2m()

    with admin_override(Group, save_related=fake_save_related):
        response = _patch(superuser_client, g.pk, {"name": "new"})
    assert response.status_code == 200
    assert calls == [True]  # change → change=True


@pytest.mark.django_db
def test_user_without_change_permission_forbidden(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    with admin_override(Group, has_change_permission=lambda self, request, obj=None: False):
        response = _patch(superuser_client, g.pk, {"name": "x"})
    assert response.status_code == 403


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.patch(
        "/admin-react/api/v1/auth/nope/1/",
        data=json.dumps({"name": "x"}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_pk_not_found(superuser_client: Client) -> None:
    response = _patch(superuser_client, 999999, {"name": "x"})
    assert response.status_code == 404


@pytest.mark.django_db
def test_bogus_pk_not_found(superuser_client: Client) -> None:
    response = _patch(superuser_client, "not-an-int", {"name": "x"})
    assert response.status_code == 404


@pytest.mark.django_db
def test_csrf_missing_on_unsafe_method_forbidden() -> None:
    from django.contrib.auth import get_user_model

    g = Group.objects.create(name="csrf")
    User = get_user_model()
    user = User.objects.create_superuser(
        username="csrf_root_patch",
        password="test-only-csrf-root-patch",  # noqa: S106
        email="csrf-patch@example.com",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.patch(
        _url(g.pk), data=json.dumps({"name": "x"}), content_type="application/json"
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_unknown_field_is_bad_request(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = _patch(superuser_client, g.pk, {"name": "x", "bogus": 1})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.django_db
def test_readonly_field_in_payload_is_bad_request(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    with admin_override(Group, get_readonly_fields=lambda self, request, obj=None: ("name",)):
        response = _patch(superuser_client, g.pk, {"name": "renamed"})
    assert response.status_code == 400
    assert "read-only" in response.json()["error"]["message"]


@pytest.mark.django_db
def test_partial_update_preserves_unspecified_fields(superuser_client: Client) -> None:
    """An empty PATCH body must not blank required fields."""
    g = Group.objects.create(name="keep")
    response = _patch(superuser_client, g.pk, {})
    assert response.status_code == 200
    g.refresh_from_db()
    assert g.name == "keep"


@pytest.mark.django_db
def test_starts_from_admin_get_queryset(superuser_client: Client) -> None:
    g = Group.objects.create(name="hidden")
    with admin_override(Group, get_queryset=lambda self, request: Group.objects.none()):
        response = _patch(superuser_client, g.pk, {"name": "x"})
    assert response.status_code == 404


@pytest.mark.django_db
def test_save_model_is_called_with_change_true(superuser_client: Client) -> None:
    g = Group.objects.create(name="orig")
    calls = []

    def fake_save_model(self, request, obj, form, change):  # noqa: ARG001
        calls.append(change)
        obj.save()

    with admin_override(Group, save_model=fake_save_model):
        response = _patch(superuser_client, g.pk, {"name": "renamed"})
    assert response.status_code == 200
    assert calls == [True]
    g.refresh_from_db()
    assert g.name == "renamed"


@pytest.mark.django_db
def test_validation_failure_returns_envelope(superuser_client: Client) -> None:
    g = Group.objects.create(name="orig")
    Group.objects.create(name="taken")
    # Name has a UNIQUE constraint on auth.Group.
    response = _patch(superuser_client, g.pk, {"name": "taken"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    assert "name" in body["error"]["fields"]
