"""Tests for ``POST /api/v1/<app>/<model>/<pk>/password/`` (#252).

Mandatory matrix from CLAUDE.md §6 + ACCEPTANCE.md §3.5 T-1, plus the
feature-specific security cases the endpoint introduces: password never
echoed/readable, mismatch + validator rejection map to fields, models
without a password-change form 404, and a self-change keeps the actor's
session alive.

The target model is ``auth.User`` (registered with Django's ``UserAdmin``,
which declares ``change_password_form``). ``auth.Group`` stands in for a
model whose admin has *no* password affordance.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.test import override_settings

from tests.helpers import admin_override

User = get_user_model()

_GOOD = "aVeryStr0ngPassw0rd!!"


def _url(pk: object) -> str:
    return f"/admin-react/api/v1/auth/user/{pk}/password/"


def _post(client: Client, pk: object, body: dict) -> object:
    return client.post(_url(pk), data=json.dumps(body), content_type="application/json")


def _make_target(username: str = "target") -> User:
    return User.objects.create_user(
        username=username,
        password="initial-password-xyz",  # noqa: S106
        email=f"{username}@example.com",
    )


# --------------------------------------------------------------------------- #
# Mandatory 8-row matrix                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_unauthorized(anon_client: Client) -> None:
    target = _make_target()
    response = _post(anon_client, target.pk, {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code in (302, 403)
    target.refresh_from_db()
    assert not target.check_password(_GOOD)


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    target = _make_target()
    response = _post(user_client, target.pk, {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code == 403
    target.refresh_from_db()
    assert not target.check_password(_GOOD)


@pytest.mark.django_db
def test_staff_with_change_permission_sets_password(superuser_client: Client) -> None:
    target = _make_target()
    response = _post(superuser_client, target.pk, {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code == 200, response.content
    target.refresh_from_db()
    # The password was hashed through set_password — the raw value verifies,
    # and the stored value is not the plaintext.
    assert target.check_password(_GOOD)
    assert target.password != _GOOD


@pytest.mark.django_db
def test_staff_without_change_permission_forbidden(superuser_client: Client) -> None:
    target = _make_target()
    with admin_override(User, has_change_permission=lambda self, request, obj=None: False):
        response = _post(superuser_client, target.pk, {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code == 403
    target.refresh_from_db()
    assert not target.check_password(_GOOD)


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.post(
        "/admin-react/api/v1/auth/nope/1/password/",
        data=json.dumps({"password1": _GOOD, "password2": _GOOD}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_pk_not_found(superuser_client: Client) -> None:
    response = _post(superuser_client, 999999, {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code == 404


@pytest.mark.django_db
def test_bogus_pk_not_found(superuser_client: Client) -> None:
    response = _post(superuser_client, "not-a-valid-id", {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code == 404


@pytest.mark.django_db
def test_csrf_missing_forbidden() -> None:
    """A password POST without a CSRF token is a 403 from middleware."""
    target = _make_target()
    actor = User.objects.create_superuser(
        username="csrf_root_pw",
        password="test-only-csrf-root-pw",  # noqa: S106
        email="csrf-pw@example.com",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    response = client.post(
        _url(target.pk),
        data=json.dumps({"password1": _GOOD, "password2": _GOOD}),
        content_type="application/json",
    )
    assert response.status_code == 403
    target.refresh_from_db()
    assert not target.check_password(_GOOD)


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_model_without_password_form_not_found(superuser_client: Client) -> None:
    """A model whose admin has no ``change_password_form`` (GroupAdmin) has
    no ``/password/`` sub-resource — 404, mirroring Django's router."""
    g = Group.objects.create(name="example")
    response = superuser_client.post(
        f"/admin-react/api/v1/auth/group/{g.pk}/password/",
        data=json.dumps({"password1": _GOOD, "password2": _GOOD}),
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_password_mismatch_is_validation_error(superuser_client: Client) -> None:
    target = _make_target()
    response = _post(superuser_client, target.pk, {"password1": _GOOD, "password2": "different"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    assert "password2" in body["error"]["fields"]
    target.refresh_from_db()
    assert not target.check_password(_GOOD)


@pytest.mark.django_db
def test_empty_body_is_validation_error(superuser_client: Client) -> None:
    """No password fields → required-field validation error, not a 500."""
    target = _make_target()
    response = _post(superuser_client, target.pk, {})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"


@pytest.mark.django_db
@override_settings(
    AUTH_PASSWORD_VALIDATORS=[
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            "OPTIONS": {"min_length": 20},
        }
    ]
)
def test_password_validators_are_enforced(superuser_client: Client) -> None:
    """The admin form runs ``AUTH_PASSWORD_VALIDATORS`` — a too-short
    password is rejected with a field error, never saved."""
    target = _make_target()
    response = _post(superuser_client, target.pk, {"password1": "short", "password2": "short"})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    assert "password2" in body["error"]["fields"]
    target.refresh_from_db()
    assert not target.check_password("short")


@pytest.mark.django_db
def test_password_never_in_response(superuser_client: Client) -> None:
    """The success body carries no password material — only a detail +
    the pk."""
    target = _make_target()
    response = _post(superuser_client, target.pk, {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code == 200
    raw = response.content.decode("utf-8")
    assert _GOOD not in raw
    target.refresh_from_db()
    assert target.password not in raw  # the hash never leaks either
    assert set(response.json().keys()) == {"detail", "id"}


@pytest.mark.django_db
def test_self_password_change_keeps_session(superuser_client: Client) -> None:
    """Changing one's OWN password keeps the session alive
    (``update_session_auth_hash``), so the next authed request still 200s."""
    # The superuser_client's user is "root"; resolve its pk.
    me = User.objects.get(username="root")
    response = _post(superuser_client, me.pk, {"password1": _GOOD, "password2": _GOOD})
    assert response.status_code == 200
    # Session survived: a subsequent authenticated request is not bounced.
    follow_up = superuser_client.get("/admin-react/api/v1/registry/")
    assert follow_up.status_code == 200


@pytest.mark.django_db
def test_malformed_json_body_is_bad_request(superuser_client: Client) -> None:
    """A non-JSON body is a 400 bad_request from ``parse_json_body``, not a
    500 — and the password is never touched."""
    target = _make_target()
    response = superuser_client.post(
        _url(target.pk), data="not json{", content_type="application/json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.django_db
def test_get_method_not_allowed(superuser_client: Client) -> None:
    target = _make_target()
    response = superuser_client.get(_url(target.pk))
    assert response.status_code == 405


# --------------------------------------------------------------------------- #
# Detail-payload affordance flag                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_detail_flag_true_for_user_with_change_permission(superuser_client: Client) -> None:
    target = _make_target()
    body = superuser_client.get(f"/admin-react/api/v1/auth/user/{target.pk}/").json()
    assert body["password_change"]["supported"] is True


@pytest.mark.django_db
def test_detail_flag_false_without_change_permission(superuser_client: Client) -> None:
    target = _make_target()
    with admin_override(User, has_change_permission=lambda self, request, obj=None: False):
        # has_change_permission=False also gates the detail view itself in
        # some flows; the detail GET uses has_view_permission, so it still
        # returns — and the password flag must be False.
        body = superuser_client.get(f"/admin-react/api/v1/auth/user/{target.pk}/").json()
    assert body["password_change"]["supported"] is False


@pytest.mark.django_db
def test_detail_flag_false_for_model_without_password_form(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    body = superuser_client.get(f"/admin-react/api/v1/auth/group/{g.pk}/").json()
    assert body["password_change"]["supported"] is False
