"""Tests for ``LogEntry`` emission on SPA writes (#155, parity).

Django's HTML admin records a ``django.contrib.admin.models.LogEntry``
row on every add / change / delete. The package must do the same when
the write goes through the SPA, so the per-object History view (and
any consumer relying on the admin audit trail) has no holes.

Covered:

- Create (POST)  → one ADDITION row, correct user, object id, repr.
- Update (PATCH) → one CHANGE row with a change message.
- Delete (DELETE)→ one DELETION row written *before* the row is gone.
- Bulk PATCH     → one CHANGE row per successfully-updated object.
- The acting user on the entry is ``request.user``.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import DELETION
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import Client

COLLECTION_URL = "/admin-react/api/v1/auth/group/"


def _detail_url(pk: int) -> str:
    return f"{COLLECTION_URL}{pk}/"


def _group_entries() -> list[LogEntry]:
    ct = ContentType.objects.get_for_model(Group)
    return list(LogEntry.objects.filter(content_type=ct).order_by("id"))


@pytest.mark.django_db
def test_create_emits_addition_logentry(superuser_client: Client) -> None:
    before = LogEntry.objects.count()
    response = superuser_client.post(
        COLLECTION_URL,
        data=json.dumps({"name": "alpha"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    pk = response.json()["pk"]

    assert LogEntry.objects.count() == before + 1
    entry = _group_entries()[-1]
    assert entry.action_flag == ADDITION
    assert entry.object_id == str(pk)
    assert entry.object_repr == "alpha"
    # The acting user is the request user (the superuser fixture).
    assert entry.user.is_superuser is True


@pytest.mark.django_db
def test_update_emits_change_logentry(superuser_client: Client) -> None:
    group = Group.objects.create(name="before")
    before = LogEntry.objects.count()

    response = superuser_client.patch(
        _detail_url(group.pk),
        data=json.dumps({"name": "after"}),
        content_type="application/json",
    )
    assert response.status_code == 200

    assert LogEntry.objects.count() == before + 1
    entry = _group_entries()[-1]
    assert entry.action_flag == CHANGE
    assert entry.object_id == str(group.pk)
    # construct_change_message produces a non-empty change message for
    # a field that actually changed.
    assert entry.get_change_message() != ""


@pytest.mark.django_db
def test_delete_emits_deletion_logentry(superuser_client: Client) -> None:
    group = Group.objects.create(name="doomed")
    pk = group.pk
    before = LogEntry.objects.count()

    response = superuser_client.delete(_detail_url(pk))
    assert response.status_code == 204
    assert not Group.objects.filter(pk=pk).exists()

    assert LogEntry.objects.count() == before + 1
    entry = _group_entries()[-1]
    assert entry.action_flag == DELETION
    # The repr was captured before the row was deleted.
    assert entry.object_repr == "doomed"
    assert entry.object_id == str(pk)


@pytest.mark.django_db
def test_bulk_patch_emits_one_change_per_row(superuser_client: Client) -> None:
    g1 = Group.objects.create(name="g1")
    g2 = Group.objects.create(name="g2")
    before = LogEntry.objects.count()

    response = superuser_client.patch(
        f"{COLLECTION_URL}bulk/",
        data=json.dumps(
            {
                "updates": [
                    {"pk": g1.pk, "fields": {"name": "g1x"}},
                    {"pk": g2.pk, "fields": {"name": "g2x"}},
                ]
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200

    # One CHANGE entry per successfully-updated row.
    assert LogEntry.objects.count() == before + 2
    entries = _group_entries()[-2:]
    assert all(e.action_flag == CHANGE for e in entries)
    assert {e.object_id for e in entries} == {str(g1.pk), str(g2.pk)}
