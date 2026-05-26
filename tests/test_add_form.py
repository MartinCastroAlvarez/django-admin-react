"""Tests for ``GET /api/v1/<app>/<model>/add/`` (#181 create flow).

The blank create-form metadata endpoint: same field/fieldset shape as
the detail response but for a new object (``obj=None``), gated by
``has_add_permission``.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from tests.helpers import admin_override

URL = "/admin-react/api/v1/auth/group/add/"


@pytest.mark.django_db
def test_anonymous_unauthorized(anon_client: Client) -> None:
    assert anon_client.get(URL).status_code in (302, 403)


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    assert user_client.get(URL).status_code == 403


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    assert superuser_client.get("/admin-react/api/v1/auth/nope/add/").status_code == 404


@pytest.mark.django_db
def test_without_add_permission_forbidden(superuser_client: Client) -> None:
    with admin_override(Group, has_add_permission=lambda self, request: False):
        assert superuser_client.get(URL).status_code == 403


@pytest.mark.django_db
def test_returns_blank_form_metadata(superuser_client: Client) -> None:
    response = superuser_client.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert body["app_label"] == "auth"
    assert body["model_name"] == "group"
    assert body["permissions"]["add"] is True
    assert isinstance(body["fieldsets"], list) and body["fieldsets"]
    # The Group form exposes a `name` field; its value is blank (no obj).
    assert "name" in body["fields"]
    assert body["fields"]["name"]["value"] in ("", None)
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_add_segment_not_swallowed_as_pk(superuser_client: Client) -> None:
    # The literal `add/` route must win over the `<pk>/` instance
    # pattern — a GET to add/ returns the form, not a 404 for pk="add".
    response = superuser_client.get(URL)
    assert response.status_code == 200
    assert "pk" not in response.json()
