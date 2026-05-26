"""Tests for ``date_hierarchy`` on the list endpoint (Issue #62).

Wire contract: ``docs/api-contract.md`` §3.1.

Covered:

- Admin without ``date_hierarchy`` declared → no ``date_hierarchy``
  key in the response (back-compat for the bulk of the matrix).
- Admin with ``date_hierarchy`` on a typo'd field → silently
  suppressed (no 500).
- Admin with ``date_hierarchy`` on a non-Date field → silently
  suppressed.
- Admin with a valid ``date_hierarchy`` field → payload present with
  ``field``, ``granularity_options``, ``active``, ``buckets``.
- Active drill-down (``?year=`` / ``?month=`` / ``?day=``) narrows
  the queryset; bucket level descends accordingly.
- Garbage query params (``?year=abc``, ``?year=-1``, ``?month=99``)
  are silently ignored, never 500.
"""

from __future__ import annotations

import contextlib
import datetime as dt
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

USER_LIST_URL = "/admin-react/api/v1/auth/user/"


@contextmanager
def admin_attr(model_cls, **values):
    """Temporarily set non-callable attributes on a registered ModelAdmin.

    Distinct from ``tests.helpers.admin_override`` which binds methods.
    ``date_hierarchy`` is a plain string attribute, not a method.
    """
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
                # The attr wasn't set on the instance before — remove
                # the override so the class-level default re-emerges.
                with contextlib.suppress(AttributeError):
                    delattr(model_admin, name)
            else:
                setattr(model_admin, name, original)


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #
@pytest.fixture
def users_across_three_months(db) -> None:  # noqa: ARG001
    """Seed three test users with ``date_joined`` in three different months.

    Drives the year / month / day drill-down tests deterministically.
    Using ``timezone.make_aware`` so the stored timestamps line up with
    Django's ``USE_TZ=True`` regardless of the test project's timezone.
    """
    User = get_user_model()
    User.objects.create_user(
        username="alice",
        password="x",  # noqa: S106
        email="a@example.com",
        date_joined=timezone.make_aware(dt.datetime(2025, 10, 5, 12, 0)),
    )
    User.objects.create_user(
        username="bob",
        password="x",  # noqa: S106
        email="b@example.com",
        date_joined=timezone.make_aware(dt.datetime(2025, 10, 20, 12, 0)),
    )
    User.objects.create_user(
        username="carol",
        password="x",  # noqa: S106
        email="c@example.com",
        date_joined=timezone.make_aware(dt.datetime(2024, 8, 1, 12, 0)),
    )


# --------------------------------------------------------------------------- #
# §3.1 contract — date_hierarchy block presence                               #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_no_date_hierarchy_when_admin_does_not_declare_it(
    superuser_client: Client,
) -> None:
    """Default admins (no ``date_hierarchy``) don't emit the block."""
    response = superuser_client.get(USER_LIST_URL)
    assert response.status_code == 200
    assert "date_hierarchy" not in response.json()


@pytest.mark.django_db
def test_typoed_field_is_silently_suppressed(superuser_client: Client) -> None:
    """A typo in ``date_hierarchy`` must not 500 the list response."""
    User = get_user_model()
    # Pretend the admin declared a non-existent field.
    with admin_attr(User, date_hierarchy="no_such_field"):
        response = superuser_client.get(USER_LIST_URL)
    # The view should still return a 200; the date_hierarchy block is
    # silently omitted. This protects against admin-author typos.
    assert response.status_code == 200


@pytest.mark.django_db
def test_non_date_field_is_silently_suppressed(superuser_client: Client) -> None:
    """``date_hierarchy`` pointing at a CharField → no payload, no 500."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="username"):
        response = superuser_client.get(USER_LIST_URL)
    assert response.status_code == 200
    assert "date_hierarchy" not in response.json()


@pytest.mark.django_db
def test_valid_date_hierarchy_emits_metadata_and_buckets(
    superuser_client: Client, users_across_three_months: None
) -> None:
    """A valid ``date_hierarchy`` field surfaces metadata + year buckets."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="date_joined"):
        response = superuser_client.get(USER_LIST_URL)
    assert response.status_code == 200
    body = response.json()
    assert "date_hierarchy" in body
    payload = body["date_hierarchy"]
    assert payload["field"] == "date_joined"
    assert payload["granularity_options"] == ["year", "month", "day"]
    assert payload["active"] == {"year": None, "month": None, "day": None}
    bucket_values = {b["value"] for b in payload["buckets"]}
    assert 2024 in bucket_values
    assert 2025 in bucket_values


# --------------------------------------------------------------------------- #
# §3.1 contract — active drill-down narrows the queryset                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_year_filter_narrows_queryset(
    superuser_client: Client, users_across_three_months: None
) -> None:
    """``?year=2025`` returns only rows whose date_joined falls in 2025."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="date_joined"):
        response = superuser_client.get(USER_LIST_URL + "?year=2025")
    body = response.json()
    usernames = {row["fields"].get("username", row["label"]) for row in body["results"]}
    assert "alice" in usernames
    assert "bob" in usernames
    assert "carol" not in usernames
    assert body["date_hierarchy"]["active"]["year"] == 2025
    # Bucket level descends to month (since year is now selected).
    assert {b["value"] for b in body["date_hierarchy"]["buckets"]} >= {10}


@pytest.mark.django_db
def test_year_and_month_filter_narrows_to_month(
    superuser_client: Client, users_across_three_months: None
) -> None:
    """``?year=2025&month=10`` returns only October 2025 rows."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="date_joined"):
        response = superuser_client.get(USER_LIST_URL + "?year=2025&month=10")
    body = response.json()
    usernames = {row["fields"].get("username", row["label"]) for row in body["results"]}
    assert "alice" in usernames
    assert "bob" in usernames
    assert "carol" not in usernames
    assert body["date_hierarchy"]["active"] == {"year": 2025, "month": 10, "day": None}
    bucket_values = {b["value"] for b in body["date_hierarchy"]["buckets"]}
    assert bucket_values == {5, 20}  # Alice on the 5th, Bob on the 20th


@pytest.mark.django_db
def test_year_month_day_filter_returns_no_further_buckets(
    superuser_client: Client, users_across_three_months: None
) -> None:
    """Selecting year+month+day narrows to that day and emits no buckets."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="date_joined"):
        response = superuser_client.get(USER_LIST_URL + "?year=2025&month=10&day=5")
    body = response.json()
    usernames = {row["fields"].get("username", row["label"]) for row in body["results"]}
    assert usernames == {"alice"}
    assert body["date_hierarchy"]["active"] == {"year": 2025, "month": 10, "day": 5}
    assert body["date_hierarchy"]["buckets"] == []


# --------------------------------------------------------------------------- #
# §3.1 contract — robustness against bad input                                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_garbage_year_param_is_ignored(
    superuser_client: Client, users_across_three_months: None
) -> None:
    """``?year=abc`` is silently dropped — no 500, no filter applied."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="date_joined"):
        response = superuser_client.get(USER_LIST_URL + "?year=abc")
    assert response.status_code == 200
    assert response.json()["date_hierarchy"]["active"] == {
        "year": None,
        "month": None,
        "day": None,
    }


@pytest.mark.django_db
def test_out_of_range_month_is_ignored(
    superuser_client: Client, users_across_three_months: None
) -> None:
    """``?year=2025&month=99`` drops the month (and so the day)."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="date_joined"):
        response = superuser_client.get(USER_LIST_URL + "?year=2025&month=99&day=5")
    assert response.status_code == 200
    active = response.json()["date_hierarchy"]["active"]
    assert active["year"] == 2025
    assert active["month"] is None
    # Day is gated on month being valid (per parse_active's design).
    assert active["day"] is None


@pytest.mark.django_db
def test_month_without_year_is_ignored(
    superuser_client: Client, users_across_three_months: None
) -> None:
    """``?month=10`` (no year) is meaningless and gets dropped."""
    User = get_user_model()
    with admin_attr(User, date_hierarchy="date_joined"):
        response = superuser_client.get(USER_LIST_URL + "?month=10")
    assert response.status_code == 200
    assert response.json()["date_hierarchy"]["active"] == {
        "year": None,
        "month": None,
        "day": None,
    }
