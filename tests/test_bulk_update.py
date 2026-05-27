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
from contextlib import suppress

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import Client

from tests.helpers import admin_override

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
                with suppress(AttributeError):
                    delattr(model_admin, name)
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
    response = anon_client.patch(BULK_URL, data="{}", content_type="application/json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_non_staff_bulk_forbidden(user_client: Client) -> None:
    response = user_client.patch(BULK_URL, data="{}", content_type="application/json")
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
    response = superuser_client.patch(BULK_URL, data="{}", content_type="application/json")
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
    with admin_attr(Group, list_editable=("name",)):
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
    with admin_attr(Group, list_editable=("name",)):
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
    with admin_attr(Group, list_editable=("name",)):
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

    # A list_editable field that's ALSO readonly is still rejected as
    # read-only (the readonly/excluded guard runs after the list_editable
    # scope check) — both protections compose.
    with admin_attr(Group, list_editable=("name",), readonly_fields=("name",)):
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
    with admin_attr(Group, list_editable=("name",)):
        response = superuser_client.patch(
            BULK_URL, data=json.dumps(payload), content_type="application/json"
        )
    assert response["Cache-Control"] == "no-store"


# --------------------------------------------------------------------------- #
# list_editable scope guard (#401): bulk PATCH may only write list_editable   #
# fields — never a field that's merely writable on the change form            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_bulk_rejects_field_not_in_list_editable(superuser_client: Client) -> None:
    """A field that is writable on the change form but NOT in list_editable is
    rejected (bad_request), and the row is left unchanged (#401)."""
    g1 = Group.objects.create(name="original")
    # list_editable is empty here, so `name` — though writable on the change
    # form — is not editable from the list.
    payload = {"updates": [{"pk": g1.pk, "fields": {"name": "hacked"}}]}
    response = superuser_client.patch(
        BULK_URL, data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["ok"] is False
    assert row["error"]["code"] == "bad_request"
    assert "not editable in the list view" in row["error"]["message"]
    g1.refresh_from_db()
    assert g1.name == "original"  # value unchanged


@pytest.mark.django_db
def test_bulk_accepts_only_the_list_editable_subset(superuser_client: Client) -> None:
    """With list_editable=('name',), `name` is accepted; a sibling writable
    field outside list_editable in the same payload is rejected (#401)."""
    g1 = Group.objects.create(name="original")
    # `permissions` is writable on the change form but not list_editable.
    payload = {"updates": [{"pk": g1.pk, "fields": {"name": "ok", "permissions": []}}]}
    with admin_attr(Group, list_editable=("name",)):
        response = superuser_client.patch(
            BULK_URL, data=json.dumps(payload), content_type="application/json"
        )
    row = response.json()["results"][0]
    assert row["ok"] is False
    assert row["error"]["code"] == "bad_request"
    assert "permissions" in row["error"]["message"]
    g1.refresh_from_db()
    assert g1.name == "original"  # atomic: nothing written


# --------------------------------------------------------------------------- #
# Coverage: malformed body, cap, per-row error envelopes (T-2)                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_bulk_malformed_json_is_bad_request(superuser_client: Client) -> None:
    """A non-JSON body → 400 from parse_json_body (bulk.py malformed path)."""
    response = superuser_client.patch(BULK_URL, data="not json{", content_type="application/json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.django_db
def test_bulk_exceeds_cap_is_bad_request(superuser_client: Client) -> None:
    """`updates` beyond the bulk cap → 400 (bulk.py cap guard)."""
    from django_admin_react.api.views.bulk import _BULK_MAX_UPDATES

    payload = {"updates": [{"pk": 1, "fields": {"name": "x"}}] * (_BULK_MAX_UPDATES + 1)}
    response = superuser_client.patch(
        BULK_URL, data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    assert "cap" in response.json()["error"]["message"].lower()


@pytest.mark.django_db
def test_bulk_per_row_error_envelopes(superuser_client: Client) -> None:
    """Per-row validation failures (bulk.py `_apply_one`) become structured
    `ok: False` envelopes — entry-not-an-object, missing pk, empty fields —
    without raising, and the batch rolls back (rejected > 0)."""
    g = Group.objects.create(name="g")
    payload = {
        "updates": [
            "not-an-object",
            {"fields": {"name": "x"}},  # missing pk
            {"pk": g.pk, "fields": {}},  # empty fields
        ]
    }
    response = superuser_client.patch(
        BULK_URL, data=json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert all(r["ok"] is False for r in results)
    codes = {r["error"]["code"] for r in results}
    assert codes == {"bad_request"}


@pytest.mark.django_db
def test_bulk_per_row_change_permission_denied(superuser_client: Client) -> None:
    """A row the user can't change becomes a `forbidden` envelope
    (bulk.py per-row change-perm gate), not a hard 403."""
    g = Group.objects.create(name="g")
    payload = {"updates": [{"pk": g.pk, "fields": {"name": "renamed"}}]}
    with admin_override(Group, has_change_permission=lambda self, request, obj=None: obj is None):
        response = superuser_client.patch(
            BULK_URL, data=json.dumps(payload), content_type="application/json"
        )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["ok"] is False
    assert results[0]["error"]["code"] == "forbidden"
    g.refresh_from_db()
    assert g.name == "g"  # unchanged (rolled back)
