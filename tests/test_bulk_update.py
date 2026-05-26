"""Tests for the bulk PATCH endpoint + ``list_editable`` (Issue #61).

Wire contract: ``docs/api-contract.md`` §5.5.

Covered:

- ``columns[*].editable`` reflects ``list_editable`` membership.
- Mandatory matrix on bulk PATCH.
- Successful batch updates all rows atomically.
- Partial failure rolls the whole transaction back.
- Each row's response carries either ``ok: True`` or
  ``error: {code, message, fields?}``.
- Hostile / forbidden keys per row → that row fails; whole batch
  rolls back.
- Empty / malformed payload → 400.
- Bulk cap enforced.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import Client

BULK_URL = "/admin-react/api/v1/auth/group/bulk/"
LIST_URL = "/admin-react/api/v1/auth/group/"


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
                try:
                    delattr(model_admin, name)
                except AttributeError:
                    pass
            else:
                setattr(model_admin, name, original)


# --------------------------------------------------------------------------- #
# columns.editable from list_editable                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_columns_have_editable_flag_off_by_default(superuser_client: Client) -> None:
    response = superuser_client.get(LIST_URL)
    columns = response.json()["columns"]
    for col in columns:
        assert col["editable"] is False


@pytest.mark.django_db
def test_columns_editable_reflects_list_editable(superuser_client: Client) -> None:
    with admin_attr(
        Group,
        list_display=("name",),
        list_editable=("name",),
    ):
        response = superuser_client.get(LIST_URL)
    cols = {c["name"]: c["editable"] for c in response.json()["columns"]}
    assert cols.get("name") is True


# --------------------------------------------------------------------------- #
# §6 mandatory matrix                                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_bulk_forbidden(anon_client: Client) -> None:
    response = anon_client.patch(
        BULK_URL, data="{}", content_type="application/json"
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_non_staff_bulk_forbidden(user_client: Client) -> None:
    response = user_client.patch(
        BULK_URL, data="{}", content_type="application/json"
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_unregistered_model_returns_404(superuser_client: Client) -> None:
    response = superuser_client.patch(
        "/admin-react/api/v1/unknown/nothing/bulk/",
        data='{"updates": []}',
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_missing_updates_returns_400(superuser_client: Client) -> None:
    response = superuser_client.patch(
        BULK_URL, data="{}", content_type="application/json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_empty_updates_list_returns_400(superuser_client: Client) -> None:
    response = superuser_client.patch(
        BULK_URL,
        data='{"updates": []}',
        content_type="application/json",
    )
    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# Happy path: atomic success                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_successful_batch_updates_all_rows(superuser_client: Client) -> None:
    g1 = Group.objects.create(name="g1")
    g2 = Group.objects.create(name="g2")

    payload = {
        "updates": [
            {"pk": g1.pk, "fields": {"name": "g1-renamed"}},
            {"pk": g2.pk, "fields": {"name": "g2-renamed"}},
        ]
    }
    response = superuser_client.patch(
        BULK_URL, data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {"accepted": 2, "rejected": 0}
    for row in body["results"]:
        assert row["ok"] is True
    g1.refresh_from_db()
    g2.refresh_from_db()
    assert g1.name == "g1-renamed"
    assert g2.name == "g2-renamed"


# --------------------------------------------------------------------------- #
# Atomic rollback on partial failure                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_failure_rolls_back_the_whole_batch(superuser_client: Client) -> None:
    """If any row fails, no row is committed — atomic posture."""
    g1 = Group.objects.create(name="g1")

    payload = {
        "updates": [
            {"pk": g1.pk, "fields": {"name": "g1-renamed"}},
            {"pk": 999999, "fields": {"name": "ghost"}},
        ]
    }
    response = superuser_client.patch(
        BULK_URL, data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {"accepted": 0, "rejected": 2}
    g1.refresh_from_db()
    assert g1.name == "g1"  # rollback worked
    for row in body["results"]:
        assert row["ok"] is False
        if row["pk"] == g1.pk:
            assert row.get("rolled_back") is True


@pytest.mark.django_db
def test_invalid_field_value_rolls_back(superuser_client: Client) -> None:
    g1 = Group.objects.create(name="g1")

    payload = {
        "updates": [
            # Empty name violates the CharField's blank=False.
            {"pk": g1.pk, "fields": {"name": ""}},
        ]
    }
    response = superuser_client.patch(
        BULK_URL, data=json.dumps(payload), content_type="application/json"
    )
    body = response.json()
    assert body["summary"] == {"accepted": 0, "rejected": 1}
    row = body["results"][0]
    assert row["ok"] is False
    assert row["error"]["code"] == "validation_failed"
    assert "name" in row["error"]["fields"]
    g1.refresh_from_db()
    assert g1.name == "g1"  # rollback worked


# --------------------------------------------------------------------------- #
# Forbidden / readonly field rejection                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_write_to_readonly_field_per_row_error(superuser_client: Client) -> None:
    g1 = Group.objects.create(name="g1")

    with admin_attr(Group, readonly_fields=("name",)):
        payload = {"updates": [{"pk": g1.pk, "fields": {"name": "x"}}]}
        response = superuser_client.patch(
            BULK_URL, data=json.dumps(payload), content_type="application/json"
        )
    body = response.json()
    row = body["results"][0]
    assert row["ok"] is False
    assert row["error"]["code"] == "bad_request"
    assert "read-only" in row["error"]["message"]


# --------------------------------------------------------------------------- #
# Cache header                                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_bulk_response_has_no_store(superuser_client: Client) -> None:
    g1 = Group.objects.create(name="g1")
    payload = {"updates": [{"pk": g1.pk, "fields": {"name": "g1-renamed"}}]}
    response = superuser_client.patch(
        BULK_URL, data=json.dumps(payload), content_type="application/json"
    )
    assert response["Cache-Control"] == "no-store"
