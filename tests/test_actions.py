"""Tests for ``ModelAdmin.actions`` + the action runner endpoint (Issue #58).

Wire contract: ``docs/api-contract.md`` §3.4 (metadata in list
response) and §5.4 (POST runner).

Covered:

- ``actions: [...]`` is always present in the list response.
- Mandatory matrix on the runner: anonymous, non-staff, staff without
  change permission, staff with permission.
- Unknown action name → 404.
- Empty / missing ``pks`` → 400.
- Action callable receives a queryset narrowed by
  ``get_queryset(request).filter(pk__in=...)``.
- CSRF on unsafe method (action is POST) → 403 without a token.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextlib import suppress

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client

from tests.helpers import admin_override

ACTIONS_BASE = "/admin-react/api/v1/auth/user/actions/"
LIST_URL = "/admin-react/api/v1/auth/user/"


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


# --------------------------------------------------------------------------- #
# actions metadata in list response                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_actions_array_always_present(superuser_client: Client) -> None:
    """The ``actions`` key is always in the list response (even if `[]`)."""
    response = superuser_client.get(LIST_URL)
    body = response.json()
    assert "actions" in body
    assert isinstance(body["actions"], list)


@pytest.mark.django_db
def test_actions_include_default_delete(superuser_client: Client) -> None:
    """The stock ``delete_selected`` action shows up for superusers."""
    response = superuser_client.get(LIST_URL)
    names = {a["name"] for a in response.json()["actions"]}
    assert "delete_selected" in names
    # delete actions get requires_confirmation hint
    for action in response.json()["actions"]:
        if action["name"] == "delete_selected":
            assert action["requires_confirmation"] is True


@pytest.mark.django_db
def test_delete_selected_label_is_interpolated(superuser_client: Client) -> None:
    """``delete_selected``'s ``%(verbose_name_plural)s`` placeholder is
    interpolated with the model's plural — never shown raw to the SPA."""
    response = superuser_client.get(LIST_URL)
    delete = next(a for a in response.json()["actions"] if a["name"] == "delete_selected")
    # The raw Django short_description is "Delete selected
    # %(verbose_name_plural)s"; the SPA must receive the finished label.
    assert "%(" not in delete["label"]
    assert "verbose_name_plural" not in delete["label"]
    assert "users" in delete["label"].lower()  # auth.User → "users"


# --------------------------------------------------------------------------- #
# §6 mandatory matrix on the runner                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_action_unauthorized(anon_client: Client) -> None:
    response = anon_client.post(
        ACTIONS_BASE + "delete_selected/",
        data='{"pks": [1]}',
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_non_staff_action_forbidden(user_client: Client) -> None:
    response = user_client.post(
        ACTIONS_BASE + "delete_selected/",
        data='{"pks": [1]}',
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_without_view_permission_returns_404(staff_client: Client) -> None:
    """Staff without view_permission on the model → 404 (not 403).

    Mirrors the list/detail endpoints' deny-by-default lookup: a
    model the user can't view doesn't even reveal which actions
    exist on it.
    """
    User = get_user_model()
    User.objects.create_user(username="a", password="x")  # noqa: S106
    with admin_override(User, has_view_permission=lambda self, request, obj=None: False):
        response = staff_client.post(
            ACTIONS_BASE + "delete_selected/",
            data='{"pks": [1]}',
            content_type="application/json",
        )
    assert response.status_code == 404


def _mark_inactive(model_admin, request, queryset):
    """Test action used by multiple test cases below."""
    return queryset.update(is_active=False)


@pytest.mark.django_db
def test_unknown_action_returns_404(superuser_client: Client) -> None:
    response = superuser_client.post(
        ACTIONS_BASE + "make_them_dance/",
        data='{"pks": [1]}',
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_empty_pks_returns_400(superuser_client: Client) -> None:
    response = superuser_client.post(
        ACTIONS_BASE + "delete_selected/",
        data='{"pks": []}',
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_missing_pks_returns_400(superuser_client: Client) -> None:
    response = superuser_client.post(
        ACTIONS_BASE + "delete_selected/",
        data="{}",
        content_type="application/json",
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# Happy path: a custom action narrows on pks ∩ get_queryset                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_custom_action_runs_over_narrowed_queryset(superuser_client: Client) -> None:
    User = get_user_model()
    u1 = User.objects.create_user(username="a", password="x", is_active=True)  # noqa: S106
    u2 = User.objects.create_user(username="b", password="x", is_active=True)  # noqa: S106
    u3 = User.objects.create_user(username="c", password="x", is_active=True)  # noqa: S106

    # Register the action on the User admin for the duration of the test.
    with admin_attr(
        User,
        actions=[_mark_inactive],
    ):
        response = superuser_client.post(
            ACTIONS_BASE + "_mark_inactive/",
            data=f'{{"pks": [{u1.pk}, {u2.pk}]}}',
            content_type="application/json",
        )
    assert response.status_code == 200
    body = response.json()
    assert body["executed"] is True
    assert body["action"] == "_mark_inactive"

    # u1 + u2 went inactive, u3 stayed active (narrowed by pks).
    u1.refresh_from_db()
    u2.refresh_from_db()
    u3.refresh_from_db()
    assert u1.is_active is False
    assert u2.is_active is False
    assert u3.is_active is True


@pytest.mark.django_db
def test_action_respects_get_queryset(superuser_client: Client) -> None:
    """Action cannot reach a row the admin's get_queryset excludes."""
    User = get_user_model()
    visible = User.objects.create_user(
        username="visible", password="x", is_active=True
    )  # noqa: S106
    hidden = User.objects.create_user(username="hidden", password="x", is_active=True)  # noqa: S106

    # Pin get_queryset to exclude ``hidden`` by pk.
    def _qs(self, request):
        return User.objects.exclude(pk=hidden.pk)

    with admin_attr(User, actions=[_mark_inactive]), admin_override(User, get_queryset=_qs):
        response = superuser_client.post(
            ACTIONS_BASE + "_mark_inactive/",
            data=f'{{"pks": [{visible.pk}, {hidden.pk}]}}',
            content_type="application/json",
        )
    assert response.status_code == 200

    visible.refresh_from_db()
    hidden.refresh_from_db()
    # The action ran on `visible`, NOT on `hidden` (despite hidden's
    # pk being in the request body).
    assert visible.is_active is False
    assert hidden.is_active is True  # The crucial assertion (Rule 10).


@pytest.mark.django_db
def test_action_response_has_no_store_cache(superuser_client: Client) -> None:
    User = get_user_model()
    u1 = User.objects.create_user(username="a", password="x")  # noqa: S106
    with admin_attr(User, actions=[_mark_inactive]):
        response = superuser_client.post(
            ACTIONS_BASE + "_mark_inactive/",
            data=f'{{"pks": [{u1.pk}]}}',
            content_type="application/json",
        )
    assert response["Cache-Control"] == "no-store"
