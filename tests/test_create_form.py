"""Tests for ``GET /api/v1/<app>/<model>/add/`` — the create-form schema.

Mirrors the mandatory matrix: anon → redirect/403, non-staff → 403,
staff with add perm → 200 + field descriptors, staff without add perm
→ 403, unregistered model → 404.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from tests.helpers import admin_override

ADD_URL = "/admin-react/api/v1/auth/group/add/"


@pytest.mark.django_db
def test_anonymous_redirected_or_forbidden(anon_client: Client) -> None:
    r = anon_client.get(ADD_URL)
    assert r.status_code in (302, 403)


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    assert user_client.get(ADD_URL).status_code == 403


@pytest.mark.django_db
def test_staff_with_add_permission_gets_schema(superuser_client: Client) -> None:
    r = superuser_client.get(ADD_URL)
    assert r.status_code == 200
    body = r.json()
    assert body["app_label"] == "auth"
    assert body["model_name"] == "group"
    assert "fieldsets" in body
    assert "fields" in body
    # No pk / label / inlines on the add form (it's for a new object).
    assert "pk" not in body
    assert "inlines" not in body
    # auth.Group has a `name` field — it should be present + writable.
    assert "name" in body["fields"]
    assert body["fields"]["name"]["readonly"] is False


@pytest.mark.django_db
def test_staff_without_add_permission_forbidden(superuser_client: Client) -> None:
    """Create is gated on has_add_permission — not view."""
    with admin_override(Group, has_add_permission=lambda self, request: False):
        r = superuser_client.get(ADD_URL)
    assert r.status_code == 403


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    assert superuser_client.get("/admin-react/api/v1/auth/nonexistent/add/").status_code == 404


@pytest.mark.django_db
def test_add_form_uses_change_false_form(superuser_client: Client) -> None:
    """The add form must be built with change=False / obj=None — Django's
    add view contract. A consumer get_form that returns a change-only
    form when change=True must not be used for the add path."""
    seen: dict[str, object] = {}
    from django import forms

    add_form = forms.modelform_factory(Group, fields=["name"])

    def branching_get_form(self, request, obj=None, change=False, **kwargs):  # noqa: ANN001
        seen["change"] = change
        seen["obj_is_none"] = obj is None
        return add_form

    with admin_override(Group, get_form=branching_get_form):
        r = superuser_client.get(ADD_URL)

    assert r.status_code == 200
    assert seen.get("change") is False
    assert seen.get("obj_is_none") is True


@pytest.mark.django_db
def test_add_form_includes_save_options_block(superuser_client: Client) -> None:
    """The create-form response carries the add-view save-flow flags (#154)
    so the SPA can render Save / Save-and-add-another / Save-and-continue.
    Computed with obj=None (add semantics): no "Save as new" on the add
    view, and Save / Save-and-add-another available to a user who can add.
    """
    body = superuser_client.get(ADD_URL).json()
    assert "save_options" in body
    so = body["save_options"]
    assert so["show_save"] is True
    assert so["show_save_and_add_another"] is True
    # "Save as new" is a change-view-only affordance — never on add.
    assert so["show_save_as_new"] is False
