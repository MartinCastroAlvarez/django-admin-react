"""Tests for ``GET /api/v1/<app>/<model>/<pk>/history/`` (#155 read half).

Mandatory matrix from ``CLAUDE.md`` §6 + feature-specific: the
timeline reflects entries the SPA write endpoints emit, ordered
newest-first, paginated, gated by per-object view permission.
"""

from __future__ import annotations

import json

import pytest
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from tests.helpers import admin_override

COLLECTION_URL = "/admin-react/api/v1/auth/group/"


def _history_url(pk: int) -> str:
    return f"{COLLECTION_URL}{pk}/history/"


def _log(group: Group, user, action=CHANGE, message="[]") -> None:
    # Create the row directly — the manager's ``log_action`` is
    # deprecated in Django 5.2 and the suite treats warnings as errors.
    LogEntry.objects.create(
        user_id=user.pk,
        content_type=ContentType.objects.get_for_model(Group),
        object_id=str(group.pk),
        object_repr=str(group),
        action_flag=action,
        change_message=message,
    )


# --------------------------------------------------------------------------- #
# Mandatory matrix                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_unauthorized(anon_client: Client) -> None:
    g = Group.objects.create(name="g")
    response = anon_client.get(_history_url(g.pk))
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    g = Group.objects.create(name="g")
    response = user_client.get(_history_url(g.pk))
    assert response.status_code == 403


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.get("/admin-react/api/v1/auth/nope/1/history/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_bogus_pk_not_found(superuser_client: Client) -> None:
    response = superuser_client.get(_history_url(999999))
    assert response.status_code == 404


@pytest.mark.django_db
def test_staff_without_view_permission_forbidden(superuser_client: Client) -> None:
    g = Group.objects.create(name="g")
    with admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
        response = superuser_client.get(_history_url(g.pk))
    assert response.status_code in (403, 404)


# --------------------------------------------------------------------------- #
# Feature behaviour                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_empty_history_returns_empty_list(superuser_client: Client) -> None:
    g = Group.objects.create(name="fresh")
    response = superuser_client.get(_history_url(g.pk))
    assert response.status_code == 200
    body = response.json()
    assert body["object"]["pk"] == g.pk
    assert body["entries"] == []
    assert body["total"] == 0
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_history_reflects_spa_write(superuser_client: Client) -> None:
    # Create through the SPA endpoint → should emit an ADDITION entry
    # (via the create view's log_addition), visible in the timeline.
    created = superuser_client.post(
        COLLECTION_URL,
        data=json.dumps({"name": "logged"}),
        content_type="application/json",
    )
    pk = created.json()["pk"]
    response = superuser_client.get(_history_url(pk))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["entries"][0]["action"] == "addition"
    assert body["entries"][0]["user"] is not None


@pytest.mark.django_db
def test_history_newest_first_and_paginated(superuser_client, django_user_model) -> None:
    g = Group.objects.create(name="g")
    user = django_user_model.objects.filter(is_superuser=True).first()
    for i in range(30):
        _log(g, user, message=json.dumps([{"changed": {"fields": [f"f{i}"]}}]))

    # Page 1, default size 25.
    r1 = superuser_client.get(_history_url(g.pk))
    b1 = r1.json()
    assert b1["total"] == 30
    assert b1["page"] == 1
    assert b1["page_size"] == 25
    assert len(b1["entries"]) == 25
    # Newest-first: ids are descending.
    ids = [e["id"] for e in b1["entries"]]
    assert ids == sorted(ids, reverse=True)

    # Page 2 has the remaining 5.
    r2 = superuser_client.get(_history_url(g.pk) + "?page=2")
    b2 = r2.json()
    assert b2["page"] == 2
    assert len(b2["entries"]) == 5


@pytest.mark.django_db
def test_structured_message_surfaced(superuser_client, django_user_model) -> None:
    g = Group.objects.create(name="g")
    user = django_user_model.objects.filter(is_superuser=True).first()
    _log(g, user, message=json.dumps([{"changed": {"fields": ["name"]}}]))
    response = superuser_client.get(_history_url(g.pk))
    entry = response.json()["entries"][0]
    assert entry["change_message_structured"] == [{"changed": {"fields": ["name"]}}]
    assert "name" in entry["change_message_human"].lower()
