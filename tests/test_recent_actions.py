"""Tests for ``GET /api/v1/recent-actions/`` — the index "Recent
actions" feed (#502).

Mandatory matrix from ``CLAUDE.md`` §6 (the relevant subset for a
collection-style, user-scoped read) plus feature behaviour: the feed is
scoped to the signed-in user, newest-first, links only to reachable
objects, and never leaks another user's actions.
"""

from __future__ import annotations

import pytest
from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import DELETION
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from tests.helpers import admin_override

URL = "/admin-react/api/v1/recent-actions/"


def _log(user, obj=None, *, action=CHANGE, repr_="thing", model=Group, object_id="1") -> LogEntry:
    return LogEntry.objects.create(
        user_id=user.pk,
        content_type=ContentType.objects.get_for_model(model),
        object_id=str(obj.pk) if obj is not None else object_id,
        object_repr=str(obj) if obj is not None else repr_,
        action_flag=action,
        change_message="[]",
    )


# --------------------------------------------------------------------------- #
# Mandatory matrix                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_unauthorized(anon_client: Client) -> None:
    response = anon_client.get(URL)
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    assert user_client.get(URL).status_code == 403


@pytest.mark.django_db
def test_staff_user_allowed(staff_client: Client) -> None:
    # AdminSite.has_permission is is_active+is_staff by default, so a staff
    # user passes the gate. The unauthenticated / non-staff 403s are covered
    # above; this asserts the staff happy path returns the feed shape.
    response = staff_client.get(URL)
    assert response.status_code == 200
    assert response.json() == {"actions": []}


# --------------------------------------------------------------------------- #
# Feature behaviour                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_empty_feed_returns_empty_list(superuser_client: Client) -> None:
    response = superuser_client.get(URL)
    assert response.status_code == 200
    assert response.json() == {"actions": []}
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_returns_own_actions_newest_first(superuser_client: Client) -> None:
    root = get_user_model().objects.get(username="root")
    g = Group.objects.create(name="g")
    first = _log(root, g, action=ADDITION)
    second = _log(root, g, action=CHANGE)
    body = superuser_client.get(URL).json()
    ids = [a["id"] for a in body["actions"]]
    # Newest-first: the later-created CHANGE precedes the ADDITION.
    assert ids == [second.id, first.id]
    assert body["actions"][0]["action"] == "changed"
    assert body["actions"][1]["action"] == "added"


@pytest.mark.django_db
def test_excludes_other_users_actions(superuser_client: Client) -> None:
    """A user sees only their own action log — never anyone else's."""
    other = get_user_model().objects.create_superuser(
        username="other", email="other@example.com", password="x"  # noqa: S106
    )
    g = Group.objects.create(name="g")
    _log(other, g, action=CHANGE)
    assert superuser_client.get(URL).json()["actions"] == []


@pytest.mark.django_db
def test_change_entry_links_to_registered_target(superuser_client: Client) -> None:
    root = get_user_model().objects.get(username="root")
    g = Group.objects.create(name="g")
    _log(root, g, action=CHANGE)
    target = superuser_client.get(URL).json()["actions"][0]["target"]
    assert target == {"app_label": "auth", "model_name": "group", "pk": str(g.pk)}


@pytest.mark.django_db
def test_deletion_entry_has_no_target(superuser_client: Client) -> None:
    """Deleted objects can't be linked — target is null, repr still shown."""
    root = get_user_model().objects.get(username="root")
    entry = _log(root, action=DELETION, repr_="gone group")
    action = superuser_client.get(URL).json()["actions"][0]
    assert action["id"] == entry.id
    assert action["target"] is None
    assert action["object_repr"] == "gone group"


@pytest.mark.django_db
def test_target_omitted_without_view_permission(superuser_client: Client) -> None:
    """The object is still listed (own action), but unlinkable when the
    user can't view that model — no link into a 403."""
    root = get_user_model().objects.get(username="root")
    g = Group.objects.create(name="g")
    _log(root, g, action=CHANGE)
    with admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
        action = superuser_client.get(URL).json()["actions"][0]
    assert action["target"] is None
    assert action["object_repr"] == str(g)


@pytest.mark.django_db
def test_target_omitted_for_unregistered_model(superuser_client: Client) -> None:
    """An action whose content type isn't admin-registered isn't linkable.

    ``Session`` has no ModelAdmin in the test project, so its entry shows
    as plain text."""
    from django.contrib.sessions.models import Session

    root = get_user_model().objects.get(username="root")
    _log(root, action=CHANGE, model=Session, object_id="abc", repr_="a session")
    action = superuser_client.get(URL).json()["actions"][0]
    assert action["target"] is None
    assert action["object_repr"] == "a session"


@pytest.mark.django_db
def test_limit_param_clamped(superuser_client: Client) -> None:
    root = get_user_model().objects.get(username="root")
    g = Group.objects.create(name="g")
    for _ in range(5):
        _log(root, g, action=CHANGE)
    # Explicit limit honoured.
    assert len(superuser_client.get(f"{URL}?limit=2").json()["actions"]) == 2
    # Bogus limit falls back to the default (>= our 5 rows).
    assert len(superuser_client.get(f"{URL}?limit=oops").json()["actions"]) == 5
    # Below the floor clamps up to 1.
    assert len(superuser_client.get(f"{URL}?limit=0").json()["actions"]) == 1


@pytest.mark.django_db
def test_default_limit_is_ten(superuser_client: Client) -> None:
    root = get_user_model().objects.get(username="root")
    g = Group.objects.create(name="g")
    for _ in range(15):
        _log(root, g, action=CHANGE)
    assert len(superuser_client.get(URL).json()["actions"]) == 10
