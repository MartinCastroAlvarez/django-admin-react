"""Tests for ``GET /api/v1/registry/`` (PR #3).

Matrix from ``CLAUDE.md`` §6 ("Test minimums") and ``SECURITY.md`` §4.
The registry endpoint is read-only, so several rows (write-to-readonly,
CSRF on unsafe methods) are not applicable and are noted where relevant.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group  # pylint: disable=imported-auth-user
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.test import Client
from django.urls import reverse

REGISTRY_URL = "/admin-react/api/v1/registry/"


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
@contextmanager
def _model_admin_override(model_cls, **method_returns) -> Iterator[None]:
    """Temporarily override ``has_*_permission`` on a registered ModelAdmin.

    Example::

        with _model_admin_override(User, has_view_permission=lambda req, obj=None: False):
            ...

    Restored on exit.
    """
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
# Auth gate                                                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_is_rejected(anon_client: Client) -> None:
    response = anon_client.get(REGISTRY_URL)
    # 302 (login redirect) or 403 — both satisfy the contract; what matters
    # is that the body never leaks model names.
    assert response.status_code in (302, 403)
    body = response.content.decode("utf-8", errors="replace").lower()
    assert "user" not in body or response.status_code == 302
    assert "group" not in body
    assert "password" not in body


@pytest.mark.django_db
def test_non_staff_authenticated_is_403(user_client: Client) -> None:
    response = user_client.get(REGISTRY_URL)
    assert response.status_code == 403
    body = response.json()
    assert body == {"error": {"code": "forbidden", "message": "You do not have permission."}}


@pytest.mark.django_db
def test_staff_but_admin_site_denies_is_403(staff_client: Client, monkeypatch) -> None:
    """If ``AdminSite.has_permission`` returns False, package follows that."""
    monkeypatch.setattr(admin.site, "has_permission", lambda request: False)
    response = staff_client.get(REGISTRY_URL)
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_superuser_gets_full_payload(superuser_client: Client) -> None:
    """A superuser has all permissions; the response is the full registry."""
    response = superuser_client.get(REGISTRY_URL)
    assert response.status_code == 200
    payload = response.json()

    # Top-level shape (docs/api-contract.md §2)
    assert set(payload.keys()) == {"mount", "user", "apps"}
    assert isinstance(payload["apps"], list)

    user_payload = payload["user"]
    assert set(user_payload.keys()) == {
        "id",
        "username",
        "is_staff",
        "is_superuser",
        "display_name",
    }
    assert user_payload["username"] == "root"
    assert user_payload["is_staff"] is True
    assert user_payload["is_superuser"] is True

    # auth.User and auth.Group are auto-registered and visible to staff
    # (modulo per-permission flags — the default UserAdmin honours
    # is_staff for module perms).
    auth_app = next((a for a in payload["apps"] if a["app_label"] == "auth"), None)
    assert auth_app is not None
    model_names = {m["model_name"] for m in auth_app["models"]}
    assert "user" in model_names
    assert "group" in model_names

    # Per-model entries carry the four-key permissions dict.
    user_model_entry = next(m for m in auth_app["models"] if m["model_name"] == "user")
    assert set(user_model_entry["permissions"].keys()) == {
        "view",
        "add",
        "change",
        "delete",
    }
    assert all(isinstance(v, bool) for v in user_model_entry["permissions"].values())
    assert user_model_entry["object_name"] == "User"


# --------------------------------------------------------------------------- #
# Filtering by ModelAdmin permission methods                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_has_module_permission_false_hides_model(superuser_client: Client) -> None:
    def deny(self, request) -> bool:  # noqa: ARG001
        return False

    with _model_admin_override(User, has_module_permission=deny):
        response = superuser_client.get(REGISTRY_URL)

    assert response.status_code == 200
    payload = response.json()
    auth_app = next((a for a in payload["apps"] if a["app_label"] == "auth"), None)
    # auth.Group may still be there; auth.User must not.
    if auth_app is not None:
        model_names = {m["model_name"] for m in auth_app["models"]}
        assert "user" not in model_names


@pytest.mark.django_db
def test_has_view_permission_false_hides_model(superuser_client: Client) -> None:
    def deny(self, request, obj=None) -> bool:  # noqa: ARG001
        return False

    with _model_admin_override(User, has_view_permission=deny):
        response = superuser_client.get(REGISTRY_URL)

    assert response.status_code == 200
    payload = response.json()
    auth_app = next((a for a in payload["apps"] if a["app_label"] == "auth"), None)
    if auth_app is not None:
        model_names = {m["model_name"] for m in auth_app["models"]}
        assert "user" not in model_names


@pytest.mark.django_db
def test_permission_booleans_reflect_modeladmin(superuser_client: Client) -> None:
    """Per-model ``permissions`` must equal what the ModelAdmin says."""

    def deny_delete(self, request, obj=None) -> bool:  # noqa: ARG001
        return False

    with _model_admin_override(User, has_delete_permission=deny_delete):
        response = superuser_client.get(REGISTRY_URL)

    payload = response.json()
    auth_app = next(a for a in payload["apps"] if a["app_label"] == "auth")
    user_entry = next(m for m in auth_app["models"] if m["model_name"] == "user")
    assert user_entry["permissions"]["delete"] is False
    # Other perms not affected.
    assert user_entry["permissions"]["view"] is True


# --------------------------------------------------------------------------- #
# Mount point                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_mount_reflects_request_path(superuser_client: Client) -> None:
    """The ``mount`` field is derived from the request URL (`ARCHITECTURE.md` §4.5)."""
    response = superuser_client.get(REGISTRY_URL)
    payload = response.json()
    assert payload["mount"] == "/admin-react/"


# --------------------------------------------------------------------------- #
# Defense-in-depth                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_response_does_not_leak_password_field_names(superuser_client: Client) -> None:
    """Registry returns model metadata, not field values — but sanity-check."""
    response = superuser_client.get(REGISTRY_URL)
    body = response.content.decode("utf-8")
    # Substrings that should never appear in a registry payload.
    for substring in ("password", "secret", "api_key", "ghp_", "Bearer "):
        assert substring not in body.lower(), substring


@pytest.mark.django_db
def test_url_resolves_via_reverse(superuser_client: Client) -> None:
    """The named URL pattern is the source of truth, not the literal string."""
    url = reverse("django_admin_react:api_v1:registry")
    assert url == REGISTRY_URL
    response = superuser_client.get(url)
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Sanity: helper assumptions                                                  #
# --------------------------------------------------------------------------- #
def test_auth_user_and_group_are_registered() -> None:
    """Guard against Django changing the default admin auto-registration."""
    assert User in admin.site._registry
    assert Group in admin.site._registry
    assert isinstance(admin.site._registry[User], UserAdmin)
    assert isinstance(admin.site._registry[Group], GroupAdmin)
