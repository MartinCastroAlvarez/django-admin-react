"""Tests for ``POST /api/v1/<app>/<model>/`` (PR #5).

Mandatory matrix from ``CLAUDE.md`` §6 + ``ACCEPTANCE.md`` §3.5 T-1.
Plus feature-specific: unknown-field rejection, readonly rejection,
validation envelope, save_model is called (never ``obj.save()``).
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.test import Client

from tests.helpers import admin_override

COLLECTION_URL = "/admin-react/api/v1/auth/group/"


def _post(client: Client, body: dict, url: str = COLLECTION_URL):
    return client.post(url, data=json.dumps(body), content_type="application/json")


# --------------------------------------------------------------------------- #
# Mandatory 8-row matrix                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_unauthorized(anon_client: Client) -> None:
    response = _post(anon_client, {"name": "new"})
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    response = _post(user_client, {"name": "new"})
    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "forbidden", "message": "You do not have permission."}
    }


@pytest.mark.django_db
def test_superuser_can_create(superuser_client: Client) -> None:
    response = _post(superuser_client, {"name": "alpha"})
    assert response.status_code == 201
    body = response.json()
    assert body["label"] == "alpha"
    assert isinstance(body["pk"], int)
    assert body["redirect"].endswith(f"/auth/group/{body['pk']}/")
    assert Group.objects.filter(pk=body["pk"]).exists()


@pytest.mark.django_db
def test_user_without_add_permission_forbidden(superuser_client: Client) -> None:
    with admin_override(Group, has_add_permission=lambda self, request: False):
        response = _post(superuser_client, {"name": "alpha"})
    assert response.status_code == 403


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = _post(superuser_client, {"name": "alpha"}, url="/admin-react/api/v1/auth/nope/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_unknown_field_is_bad_request(superuser_client: Client) -> None:
    response = _post(superuser_client, {"name": "alpha", "bogus_attr": "x"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"


@pytest.mark.django_db
def test_csrf_missing_on_unsafe_method_forbidden() -> None:
    """CSRF middleware must reject an authenticated POST without a token."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_superuser(
        username="csrf_root",
        password="test-only-csrf-root",  # noqa: S106
        email="csrf@example.com",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.post(
        COLLECTION_URL, data=json.dumps({"name": "alpha"}), content_type="application/json"
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_readonly_field_in_payload_is_bad_request(superuser_client: Client) -> None:
    with admin_override(Group, get_readonly_fields=lambda self, request, obj=None: ("name",)):
        response = _post(superuser_client, {"name": "alpha"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"
    assert "read-only" in body["error"]["message"]


@pytest.mark.django_db
def test_validation_failure_returns_envelope(superuser_client: Client) -> None:
    """Empty name violates Group's required-name validator."""
    response = _post(superuser_client, {"name": ""})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    assert "name" in body["error"]["fields"]


@pytest.mark.django_db
def test_save_model_is_called_not_obj_save(superuser_client: Client) -> None:
    """Confirm writes flow through ModelAdmin.save_model (B-3)."""
    calls = []

    def fake_save_model(self, request, obj, form, change):  # noqa: ARG001
        obj.name = obj.name + "_via_admin"
        obj.save()
        calls.append((obj.name, change))

    with admin_override(Group, save_model=fake_save_model):
        response = _post(superuser_client, {"name": "beta"})
    assert response.status_code == 201
    assert calls == [("beta_via_admin", False)]


@pytest.mark.django_db
def test_malformed_json_is_bad_request(superuser_client: Client) -> None:
    response = superuser_client.post(
        COLLECTION_URL, data="not json{", content_type="application/json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.django_db
def test_sensitive_field_name_rejected(superuser_client: Client) -> None:
    """Even a malicious 'password' key in the payload must be rejected."""
    response = _post(superuser_client, {"name": "alpha", "password_hash": "x"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.django_db
def test_db_integrity_error_returns_clean_409(superuser_client: Client) -> None:
    """A DB IntegrityError at save (a constraint the form didn't catch, or a
    uniqueness race) returns a clean 409 conflict envelope — not an uncaught
    500 with a driver traceback — and persists nothing (#404)."""

    def raise_integrity(self, request, obj, form, change):  # noqa: ANN001
        raise IntegrityError("simulated unique violation")

    with admin_override(Group, save_model=raise_integrity):
        response = _post(superuser_client, {"name": "fresh-name"})
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "conflict"
    assert "constraint" in body["error"]["message"].lower()
    assert response["Cache-Control"] == "no-store"
    # The atomic block rolled back — nothing persisted, no DB-detail leak.
    assert not Group.objects.filter(name="fresh-name").exists()
