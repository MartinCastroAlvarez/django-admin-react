"""Tests for object-level change-page actions (Issue #236).

These cover both halves of the feature:

- The detail payload's optional ``object_actions`` block (omitted for a
  plain-Django admin, present + permission-gated when the admin exposes
  the django-object-actions ``change_actions`` / ``get_change_actions``
  contract).
- The ``POST /api/v1/<app>/<model>/<pk>/action/<name>/`` runner, with the
  mandatory security matrix from CLAUDE.md §6.

We never add ``django-object-actions`` as a dependency — instead each
test wires the *same contract* onto a registered admin (``auth.User``):
``change_actions`` (a list of names), a ``get_change_actions`` hook that
filters by permission, and the action callables bound as methods on the
admin instance (django-object-actions binds them the same way, so
``getattr(model_admin, name)`` resolves the bound callable, called as
``method(request, obj)``).
"""

from __future__ import annotations

from contextlib import contextmanager
from contextlib import suppress

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.test import Client

User = get_user_model()

DETAIL_URL = "/admin-react/api/v1/auth/user/{pk}/"
ACTION_URL = "/admin-react/api/v1/auth/user/{pk}/action/{name}/"


# --------------------------------------------------------------------------- #
# Test scaffolding — emulate the django-object-actions admin contract        #
# --------------------------------------------------------------------------- #
@contextmanager
def admin_attr(model_cls, **values):
    """Temporarily set attributes (incl. bound methods) on a ModelAdmin.

    Functions are bound to the admin instance with ``__get__`` so that
    ``getattr(model_admin, name)`` returns a bound method called as
    ``method(request, obj)`` — exactly how django-object-actions exposes
    its actions.
    """
    model_admin = admin.site._registry[model_cls]
    sentinel = object()
    originals: dict = {}
    try:
        for name, value in values.items():
            originals[name] = model_admin.__dict__.get(name, sentinel)
            bound = value.__get__(model_admin) if callable(value) else value
            setattr(model_admin, name, bound)
        yield
    finally:
        for name, original in originals.items():
            if original is sentinel:
                with suppress(AttributeError):
                    delattr(model_admin, name)
            else:
                setattr(model_admin, name, original)


# An object action: ``method(self, request, obj)``. Marks the user
# inactive so the test can assert the side effect actually happened.
def _deactivate(self, request, obj):  # noqa: ANN001, ANN202, ARG001
    """Deactivate this account."""
    obj.is_active = False
    obj.save(update_fields=["is_active"])


_deactivate.label = "Deactivate"  # django-object-actions ``label`` attr
# ``allowed_permissions`` style marker the get_change_actions hook below
# uses to gate this action behind change permission.
_deactivate.allowed_permissions = ("change",)


def _redirecting(self, request, obj):  # noqa: ANN001, ANN202, ARG001
    """Go somewhere else after running."""
    return HttpResponseRedirect("/admin-react/auth/user/")


def _boom(self, request, obj):  # noqa: ANN001, ANN202, ARG001
    """Raise on purpose."""
    raise ValueError("the action blew up")


def _make_get_change_actions(*action_names):
    """Build a ``get_change_actions`` hook gated by ``allowed_permissions``.

    Mirrors django-object-actions' permission filtering: an action whose
    ``allowed_permissions`` the user fails is dropped from the returned
    list, so the SPA never sees it and the runner 404s it.
    """

    def get_change_actions(self, request, context, object_id):  # noqa: ANN001, ANN202, ARG001
        allowed = []
        for name in action_names:
            tool = getattr(self, name, None)
            perms = getattr(tool, "allowed_permissions", ())
            if all(
                getattr(self, f"has_{p}_permission")(request) for p in perms
            ):
                allowed.append(name)
        return allowed

    return get_change_actions


def _objaction_admin(*, with_hook=True):
    """The admin-attr kwargs that wire up the object-action contract."""
    kwargs = {
        "change_actions": ["_deactivate"],
        "_deactivate": _deactivate,
    }
    if with_hook:
        kwargs["get_change_actions"] = _make_get_change_actions("_deactivate")
    return kwargs


def _make_user(username: str = "subject", *, is_active: bool = True) -> User:
    return User.objects.create_user(
        username=username,
        password="initial-password-xyz",  # noqa: S106
        email=f"{username}@example.com",
        is_active=is_active,
    )


def _post(client: Client, pk: object, name: str) -> object:
    return client.post(ACTION_URL.format(pk=pk, name=name), content_type="application/json")


# --------------------------------------------------------------------------- #
# Detail payload: object_actions block                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_detail_omits_object_actions_for_plain_admin(superuser_client: Client) -> None:
    """A plain-Django admin (no change_actions) emits NO object_actions key."""
    u = _make_user()
    body = superuser_client.get(DETAIL_URL.format(pk=u.pk)).json()
    assert "object_actions" not in body


@pytest.mark.django_db
def test_detail_exposes_object_actions(superuser_client: Client) -> None:
    """An admin with the django-object-actions contract surfaces the
    action's name + label + description."""
    u = _make_user()
    with admin_attr(User, **_objaction_admin()):
        body = superuser_client.get(DETAIL_URL.format(pk=u.pk)).json()
    assert "object_actions" in body
    actions = {a["name"]: a for a in body["object_actions"]}
    assert "_deactivate" in actions
    assert actions["_deactivate"]["label"] == "Deactivate"  # ``label`` attr wins
    assert actions["_deactivate"]["description"] == "Deactivate this account."


@pytest.mark.django_db
def test_detail_humanizes_label_without_label_attr(superuser_client: Client) -> None:
    """When the action has no ``label`` attr, the name is humanized
    (``send_welcome_email`` → ``Send welcome email``), matching
    django-object-actions' ``capfirst(name.replace("_", " "))``."""

    def send_welcome_email(self, request, obj):  # noqa: ANN001, ANN202, ARG001
        return None

    with admin_attr(
        User,
        change_actions=["send_welcome_email"],
        send_welcome_email=send_welcome_email,
        get_change_actions=_make_get_change_actions("send_welcome_email"),
    ):
        u = _make_user()
        body = superuser_client.get(DETAIL_URL.format(pk=u.pk)).json()
    action = next(a for a in body["object_actions"] if a["name"] == "send_welcome_email")
    assert action["label"] == "Send welcome email"  # capfirst(name.replace("_", " "))


@pytest.mark.django_db
def test_detail_change_actions_attr_without_hook(superuser_client: Client) -> None:
    """An admin that declares ``change_actions`` but no ``get_change_actions``
    hook still surfaces the actions (gated at run time by change perm)."""
    u = _make_user()
    with admin_attr(User, **_objaction_admin(with_hook=False)):
        body = superuser_client.get(DETAIL_URL.format(pk=u.pk)).json()
    assert {a["name"] for a in body["object_actions"]} == {"_deactivate"}


@pytest.mark.django_db
def test_detail_fallback_filters_by_allowed_permissions(superuser_client: Client) -> None:
    """Defense in depth (#455): without ``get_change_actions``, the
    ``change_actions`` fallback also filters each declared action by its
    callable's ``allowed_permissions`` against ``has_<perm>_permission``,
    mirroring Django's ``_filter_actions_by_permissions``. An action whose
    required perm fails is dropped from ``object_actions``."""
    u = _make_user()

    def _delete_action(self, request, queryset):  # noqa: ANN001, ANN202, ARG001
        queryset.delete()

    _delete_action.allowed_permissions = ("delete",)

    def _no_delete(self, request, obj=None):  # noqa: ANN001, ANN202, ARG001
        return False

    with admin_attr(
        User,
        change_actions=["_delete_action"],
        _delete_action=_delete_action,
        has_delete_permission=_no_delete,
    ):
        body = superuser_client.get(DETAIL_URL.format(pk=u.pk)).json()
    # _delete_action requires `delete`; the admin denies → action dropped.
    assert body["object_actions"] == []


@pytest.mark.django_db
def test_detail_filters_unpermitted_actions(superuser_client: Client) -> None:
    """An action the user is not permitted to run (per get_change_actions)
    does not appear in object_actions."""
    u = _make_user()

    def _deny_all(self, request, context, object_id):  # noqa: ANN001, ANN202, ARG001
        return []

    with admin_attr(
        User,
        change_actions=["_deactivate"],
        _deactivate=_deactivate,
        get_change_actions=_deny_all,
    ):
        body = superuser_client.get(DETAIL_URL.format(pk=u.pk)).json()
    assert body["object_actions"] == []


# --------------------------------------------------------------------------- #
# §6 mandatory matrix on the runner                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_action_unauthorized(anon_client: Client) -> None:
    u = _make_user()
    with admin_attr(User, **_objaction_admin()):
        response = _post(anon_client, u.pk, "_deactivate")
    assert response.status_code in (302, 403)
    u.refresh_from_db()
    assert u.is_active is True  # never ran


@pytest.mark.django_db
def test_non_staff_action_forbidden(user_client: Client) -> None:
    u = _make_user()
    with admin_attr(User, **_objaction_admin()):
        response = _post(user_client, u.pk, "_deactivate")
    assert response.status_code == 403
    u.refresh_from_db()
    assert u.is_active is True


@pytest.mark.django_db
def test_staff_without_change_permission_forbidden(superuser_client: Client) -> None:
    """A user without change permission on the object is 403 — object
    actions are change-shaped."""
    u = _make_user()
    from tests.helpers import admin_override

    with (
        admin_attr(User, **_objaction_admin()),
        admin_override(User, has_change_permission=lambda self, request, obj=None: False),
    ):
        response = _post(superuser_client, u.pk, "_deactivate")
    assert response.status_code == 403
    u.refresh_from_db()
    assert u.is_active is True  # callable never ran


@pytest.mark.django_db
def test_staff_with_permission_runs_action(superuser_client: Client) -> None:
    u = _make_user()
    with admin_attr(User, **_objaction_admin()):
        response = _post(superuser_client, u.pk, "_deactivate")
    assert response.status_code == 200, response.content
    assert response.json() == {"ok": True}
    u.refresh_from_db()
    assert u.is_active is False  # the action ran


@pytest.mark.django_db
def test_unknown_action_name_not_found(superuser_client: Client) -> None:
    u = _make_user()
    with admin_attr(User, **_objaction_admin()):
        response = _post(superuser_client, u.pk, "_does_not_exist")
    assert response.status_code == 404


@pytest.mark.django_db
def test_action_not_permitted_is_not_found(superuser_client: Client) -> None:
    """An action listed in ``change_actions`` but dropped by
    ``get_change_actions`` (e.g. a per-action permission fail) → 404, and
    the callable never runs.

    Change permission on the object stays True (so the run reaches the
    permitted-set gate, not the change-perm gate) — isolating the
    fail-closed behaviour of the permitted-set check itself.
    """
    u = _make_user()

    def _hook_drops_it(self, request, context, object_id):  # noqa: ANN001, ANN202, ARG001
        # ``_deactivate`` is declared in change_actions but the hook
        # returns it as NOT permitted for this user.
        return []

    with admin_attr(
        User,
        change_actions=["_deactivate"],
        _deactivate=_deactivate,
        get_change_actions=_hook_drops_it,
    ):
        response = _post(superuser_client, u.pk, "_deactivate")
    assert response.status_code == 404
    u.refresh_from_db()
    assert u.is_active is True  # callable never ran — no privilege bypass


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.post(
        "/admin-react/api/v1/auth/nope/1/action/_deactivate/",
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_pk_not_found(superuser_client: Client) -> None:
    with admin_attr(User, **_objaction_admin()):
        response = _post(superuser_client, 999999, "_deactivate")
    assert response.status_code == 404


@pytest.mark.django_db
def test_csrf_missing_forbidden() -> None:
    """An action POST without a CSRF token is a 403 from middleware — the
    view is not csrf_exempt."""
    u = _make_user()
    actor = User.objects.create_superuser(
        username="csrf_root_oa",
        password="test-only-csrf-root-oa",  # noqa: S106
        email="csrf-oa@example.com",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    with admin_attr(User, **_objaction_admin()):
        response = client.post(
            ACTION_URL.format(pk=u.pk, name="_deactivate"),
            content_type="application/json",
        )
    assert response.status_code == 403
    u.refresh_from_db()
    assert u.is_active is True


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_action_returning_redirect_is_surfaced(superuser_client: Client) -> None:
    """When the callable returns a redirect HttpResponse, its URL is in
    ``redirect`` and the API response is 200 (never a 302)."""
    u = _make_user()
    with admin_attr(
        User,
        change_actions=["_redirecting"],
        _redirecting=_redirecting,
        get_change_actions=_make_get_change_actions("_redirecting"),
    ):
        response = _post(superuser_client, u.pk, "_redirecting")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["redirect"] == "/admin-react/auth/user/"


@pytest.mark.django_db
def test_action_that_raises_is_clean_400(superuser_client: Client) -> None:
    """A raising action callable → ``{ok: false, error}`` 400, never a 500."""
    u = _make_user()
    with admin_attr(
        User,
        change_actions=["_boom"],
        _boom=_boom,
        get_change_actions=_make_get_change_actions("_boom"),
    ):
        response = _post(superuser_client, u.pk, "_boom")
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert "error" in body
    # The internal exception text never leaks onto the wire.
    assert "blew up" not in response.content.decode("utf-8")


@pytest.mark.django_db
def test_action_response_has_no_store_cache(superuser_client: Client) -> None:
    u = _make_user()
    with admin_attr(User, **_objaction_admin()):
        response = _post(superuser_client, u.pk, "_deactivate")
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_get_method_not_allowed(superuser_client: Client) -> None:
    u = _make_user()
    with admin_attr(User, **_objaction_admin()):
        response = superuser_client.get(ACTION_URL.format(pk=u.pk, name="_deactivate"))
    assert response.status_code == 405


@pytest.mark.django_db
def test_runner_404s_when_admin_has_no_object_actions(superuser_client: Client) -> None:
    """A plain admin (no change_actions / get_change_actions) → the action
    endpoint 404s (the affordance doesn't exist for this model)."""
    u = _make_user()
    response = _post(superuser_client, u.pk, "_deactivate")
    assert response.status_code == 404
    u.refresh_from_db()
    assert u.is_active is True
