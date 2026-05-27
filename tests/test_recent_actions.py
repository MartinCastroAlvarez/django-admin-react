"""Tests for ``GET /api/v1/recent-actions/`` (#502 backend read half).

Mandatory matrix from ``CLAUDE.md`` §6 + the feature-specific cases the
issue prescribes: the feed is the requesting user's own ``LogEntry`` rows
(never another user's), newest-first, capped; deep-links are omitted for
deletions and for targets the user can't view, and a stale/unregistered
content type never 500s.
"""

from __future__ import annotations

import pytest
from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import DELETION
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from tests.helpers import admin_override

URL = "/admin-react/api/v1/recent-actions/"


def _root(django_user_model):
    return django_user_model.objects.get(username="root")


def _log(
    user,
    *,
    obj=None,
    content_type=None,
    object_id=None,
    object_repr=None,
    action=CHANGE,
) -> LogEntry:
    # Create the row directly — the manager's ``log_action`` is deprecated
    # in Django 5.2 and the suite treats warnings as errors.
    if content_type is None and obj is not None:
        content_type = ContentType.objects.get_for_model(type(obj))
    if object_id is None and obj is not None:
        object_id = str(obj.pk)
    if object_repr is None:
        object_repr = str(obj) if obj is not None else "thing"
    return LogEntry.objects.create(
        user_id=user.pk,
        content_type=content_type,
        object_id=object_id,
        object_repr=object_repr,
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
    # No body leakage: a 403 carries only the opaque error envelope.
    if response.status_code == 403:
        assert set(response.json()) == {"error"}


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    response = user_client.get(URL)
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_sees_only_their_own_entries(superuser_client, django_user_model) -> None:
    root = _root(django_user_model)
    other = django_user_model.objects.create_user(
        username="other", password="x", is_staff=True  # noqa: S106
    )

    g = Group.objects.create(name="g")
    _log(root, obj=g, object_repr="mine")
    _log(other, obj=g, object_repr="theirs")

    body = superuser_client.get(URL).json()
    reprs = [e["object_repr"] for e in body["entries"]]
    assert "mine" in reprs
    assert "theirs" not in reprs


@pytest.mark.django_db
def test_cache_control_no_store(superuser_client: Client) -> None:
    response = superuser_client.get(URL)
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"


# --------------------------------------------------------------------------- #
# Feature behaviour                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_empty_feed_returns_empty_list(superuser_client: Client) -> None:
    body = superuser_client.get(URL).json()
    assert body["entries"] == []
    assert body["limit"] == 10


@pytest.mark.django_db
def test_newest_first_and_capped_at_default_limit(superuser_client, django_user_model) -> None:
    root = _root(django_user_model)

    g = Group.objects.create(name="g")
    for _i in range(15):
        _log(root, obj=g)
    body = superuser_client.get(URL).json()
    assert body["limit"] == 10
    assert len(body["entries"]) == 10
    ids = [e["id"] for e in body["entries"]]
    assert ids == sorted(ids, reverse=True)  # newest action first


@pytest.mark.django_db
def test_limit_param_respected_and_clamped(superuser_client, django_user_model) -> None:
    root = _root(django_user_model)

    g = Group.objects.create(name="g")
    for _i in range(5):
        _log(root, obj=g)
    # Honoured.
    assert len(superuser_client.get(URL + "?limit=3").json()["entries"]) == 3
    # Bogus → default, not a 500.
    bogus = superuser_client.get(URL + "?limit=not-a-number")
    assert bogus.status_code == 200
    assert bogus.json()["limit"] == 10
    # Above the ceiling → clamped to the max.
    assert superuser_client.get(URL + "?limit=9999").json()["limit"] == 100


@pytest.mark.django_db
def test_viewable_change_entry_has_link(superuser_client, django_user_model) -> None:
    root = _root(django_user_model)

    g = Group.objects.create(name="linkable")
    _log(root, obj=g, action=CHANGE)
    entry = superuser_client.get(URL).json()["entries"][0]
    assert entry["action"] == "change"
    assert entry["link"] == {"app_label": "auth", "model_name": "group", "pk": str(g.pk)}
    assert entry["content_type"]["model"] == "group"


@pytest.mark.django_db
def test_deletion_has_no_link(superuser_client, django_user_model) -> None:
    """A deletion's target no longer exists — link omitted (like Django)."""
    root = _root(django_user_model)

    g = Group.objects.create(name="gone")
    _log(root, obj=g, action=DELETION)
    entry = superuser_client.get(URL).json()["entries"][0]
    assert entry["action"] == "deletion"
    assert entry["link"] is None
    # The entry is still listed, label-only.
    assert entry["object_repr"] == "gone"


@pytest.mark.django_db
def test_unviewable_target_listed_without_link(superuser_client, django_user_model) -> None:
    root = _root(django_user_model)

    g = Group.objects.create(name="secret")
    _log(root, obj=g, action=ADDITION)
    with admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
        entry = superuser_client.get(URL).json()["entries"][0]
    # Listed (Django lists it), but no link to a page the user can't open.
    assert entry["object_repr"] == "secret"
    assert entry["link"] is None
    assert entry["content_type"]["model"] == "group"


@pytest.mark.django_db
def test_stale_or_unregistered_content_type_no_link_no_500(
    superuser_client, django_user_model
) -> None:
    """An entry whose model is unregistered / its class is gone: present,
    label-only, no link, and never a 500 (the ``ContentType.name``
    fallback handles a vanished model class)."""
    root = _root(django_user_model)
    ghost = ContentType.objects.create(app_label="ghost", model="phantom")
    _log(root, content_type=ghost, object_id="7", object_repr="ghost-row", action=CHANGE)
    response = superuser_client.get(URL)
    assert response.status_code == 200
    entry = response.json()["entries"][0]
    assert entry["object_repr"] == "ghost-row"
    assert entry["link"] is None
    # Labels still surface (name falls back to the raw model string).
    assert entry["content_type"]["app_label"] == "ghost"
    assert entry["content_type"]["model"] == "phantom"


@pytest.mark.django_db
def test_null_content_type_no_link_no_500(superuser_client, django_user_model) -> None:
    """A ``LogEntry`` with a null content type (legacy rows) is listed
    with ``content_type: null`` and no link, never a 500."""
    root = _root(django_user_model)
    _log(root, content_type=None, object_id=None, object_repr="orphan", action=CHANGE)
    response = superuser_client.get(URL)
    assert response.status_code == 200
    entry = response.json()["entries"][0]
    assert entry["content_type"] is None
    assert entry["link"] is None
    assert entry["object_repr"] == "orphan"
