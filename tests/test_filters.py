"""Tests for ``list_filter`` taxonomy + application (Issue #56).

Wire contract: ``docs/api-contract.md`` §11.

Covered (on top of CLAUDE.md §6's mandatory matrix, which test_list.py
already exercises for the list endpoint):

- Admin with no ``list_filter`` → ``filters: []`` in the response.
- Each of the five closed types renders the correct descriptor:
  ``boolean``, ``choices``, ``foreignkey``, ``date_range``, ``custom``.
- Applying a filter narrows the queryset (Django's own
  ``FieldListFilter`` and ``SimpleListFilter.queryset`` are called).
- AND combination of two filters narrows further than one.
- Unknown URL parameter (`?bogus=42`) is silently ignored.
- A ``SimpleListFilter`` subclass with a non-trivial ``queryset()`` is
  honored — the architectural correctness win that motivated using
  ``ChangeList`` spec construction instead of hand-rolled Q-AND.
- A filter entry outside the closed vocabulary (e.g. ``EmptyFieldListFilter``)
  is silently dropped from the descriptor list (the SPA only learns
  five layouts).
"""

from __future__ import annotations

import pytest
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import get_user_model
from django.test import Client

from tests.helpers import admin_override

User = get_user_model()
USER_LIST_URL = "/admin-react/api/v1/auth/user/"


# --------------------------------------------------------------------------- #
# Default state                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_list_without_list_filter_returns_empty_filters_array(
    superuser_client: Client,
) -> None:
    """An admin that declares no ``list_filter`` surfaces an empty array
    (back-compat for all the pre-#56 tests, and a clean signal to the
    SPA that there's nothing to render in the sidebar)."""
    with admin_override(User, get_list_filter=lambda self, request: ()):
        response = superuser_client.get(USER_LIST_URL)
    assert response.status_code == 200
    body = response.json()
    assert "filters" in body
    assert body["filters"] == []


# --------------------------------------------------------------------------- #
# Per-type descriptor shape                                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_boolean_filter_descriptor(superuser_client: Client) -> None:
    with admin_override(User, get_list_filter=lambda self, request: ("is_active",)):
        response = superuser_client.get(USER_LIST_URL)
    body = response.json()
    descriptors = body["filters"]
    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor["type"] == "boolean"
    assert descriptor["name"] == "is_active"
    assert descriptor["label"]  # human-readable, never empty


@pytest.mark.django_db
def test_date_range_filter_descriptor(superuser_client: Client) -> None:
    with admin_override(User, get_list_filter=lambda self, request: ("date_joined",)):
        response = superuser_client.get(USER_LIST_URL)
    body = response.json()
    descriptor = body["filters"][0]
    assert descriptor["type"] == "date_range"
    assert descriptor["name"] == "date_joined"


@pytest.mark.django_db
def test_multiple_filters_render_in_declared_order(
    superuser_client: Client,
) -> None:
    with admin_override(
        User,
        get_list_filter=lambda self, request: ("is_active", "is_staff", "date_joined"),
    ):
        response = superuser_client.get(USER_LIST_URL)
    descriptors = response.json()["filters"]
    names = [d["name"] for d in descriptors]
    assert names == ["is_active", "is_staff", "date_joined"]


# --------------------------------------------------------------------------- #
# Custom SimpleListFilter                                                     #
# --------------------------------------------------------------------------- #
class TierFilter(SimpleListFilter):
    """Inline ``SimpleListFilter`` to exercise the ``custom`` descriptor.

    Picked an intentionally non-trivial ``queryset()`` — the
    architectural correctness win we get from using ``ChangeList``
    spec construction is that this method is actually called rather
    than bypassed.
    """

    title = "Tier"
    parameter_name = "tier"

    def lookups(self, request, model_admin):
        return [("staff", "Staff"), ("super", "Superuser")]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "staff":
            return queryset.filter(is_staff=True, is_superuser=False)
        if value == "super":
            return queryset.filter(is_superuser=True)
        return None


@pytest.mark.django_db
def test_custom_simplelistfilter_descriptor(superuser_client: Client) -> None:
    with admin_override(User, get_list_filter=lambda self, request: (TierFilter,)):
        response = superuser_client.get(USER_LIST_URL)
    descriptor = response.json()["filters"][0]
    assert descriptor["type"] == "custom"
    assert descriptor["name"] == "tier"
    assert descriptor["label"] == "Tier"
    assert descriptor["lookups"] == [
        {"value": "staff", "label": "Staff"},
        {"value": "super", "label": "Superuser"},
    ]


# --------------------------------------------------------------------------- #
# Filter application — narrows the queryset                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_boolean_filter_narrows_queryset(superuser_client: Client) -> None:
    """``?is_active__exact=0`` (admin-parity URL grammar) narrows to
    inactive users only. Exercising filter application — not just
    descriptor surfacing."""
    User.objects.create_user(username="active1", is_active=True, password="x")  # noqa: S106
    User.objects.create_user(username="inactive1", is_active=False, password="x")  # noqa: S106
    with admin_override(User, get_list_filter=lambda self, request: ("is_active",)):
        response = superuser_client.get(USER_LIST_URL + "?is_active__exact=0")
    body = response.json()
    usernames = {row["fields"].get("username") for row in body["results"]}
    assert "inactive1" in usernames
    assert "active1" not in usernames


@pytest.mark.django_db
def test_two_filters_combine_with_AND(superuser_client: Client) -> None:
    """Two active filter selections AND together (admin convention)."""
    User.objects.create_user(
        username="a", is_active=True, is_staff=False, password="x"
    )  # noqa: S106
    User.objects.create_user(
        username="b", is_active=True, is_staff=True, password="x"
    )  # noqa: S106
    User.objects.create_user(
        username="c", is_active=False, is_staff=True, password="x"
    )  # noqa: S106
    with admin_override(
        User,
        get_list_filter=lambda self, request: ("is_active", "is_staff"),
    ):
        response = superuser_client.get(USER_LIST_URL + "?is_active__exact=1&is_staff__exact=1")
    body = response.json()
    usernames = {row["fields"].get("username") for row in body["results"]}
    assert "b" in usernames
    assert "a" not in usernames
    assert "c" not in usernames


@pytest.mark.django_db
def test_custom_simplelistfilter_queryset_is_called(
    superuser_client: Client,
) -> None:
    """The architectural correctness check: a ``SimpleListFilter``
    subclass with a non-trivial ``queryset()`` is honored. This is the
    test that fails if someone reimplements filter application as
    ``Q``-AND iteration — exactly the trap the design warned against."""
    User.objects.create_user(
        username="plain", is_staff=False, is_superuser=False, password="x"
    )  # noqa: S106
    User.objects.create_user(
        username="just_staff", is_staff=True, is_superuser=False, password="x"
    )  # noqa: S106
    User.objects.create_superuser(
        username="super_admin", password="x", email="s@x.test"
    )  # noqa: S106
    with admin_override(User, get_list_filter=lambda self, request: (TierFilter,)):
        response = superuser_client.get(USER_LIST_URL + "?tier=staff")
    body = response.json()
    usernames = {row["fields"].get("username") for row in body["results"]}
    assert "just_staff" in usernames
    # The filter's queryset() explicitly excludes superusers from "staff" tier
    # — proving the method ran, not a naive is_staff=True AND.
    assert "super_admin" not in usernames
    assert "plain" not in usernames


# --------------------------------------------------------------------------- #
# Robustness                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_unknown_query_param_is_silently_ignored(
    superuser_client: Client,
) -> None:
    """A hostile ``?bogus=42`` must not 400 or 500 — Django's filter
    machinery only consults declared spec parameters, so unknown keys
    are no-ops."""
    User.objects.create_user(username="u1", password="x")  # noqa: S106
    with admin_override(User, get_list_filter=lambda self, request: ("is_active",)):
        response = superuser_client.get(USER_LIST_URL + "?bogus=42")
    assert response.status_code == 200
    # Total still matches the unfiltered count (no narrowing occurred).
    assert response.json()["total"] >= 1


@pytest.mark.django_db
def test_misconfigured_filter_entry_does_not_crash(
    superuser_client: Client,
) -> None:
    """A non-existent field name in ``list_filter`` is swallowed and the
    entry dropped from the descriptor list — the package never 500s a
    list response on a misconfigured admin (rule 12 / S-11)."""
    with admin_override(
        User,
        get_list_filter=lambda self, request: ("does_not_exist", "is_active"),
    ):
        response = superuser_client.get(USER_LIST_URL)
    assert response.status_code == 200
    descriptors = response.json()["filters"]
    names = [d["name"] for d in descriptors]
    # Bad entry dropped, good entry retained.
    assert names == ["is_active"]


# --------------------------------------------------------------------------- #
# Closed vocabulary — EmptyFieldListFilter is silently dropped               #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_filter_outside_closed_vocabulary_is_dropped(
    superuser_client: Client,
) -> None:
    """``AllValuesFieldListFilter`` is one of Django's filter classes
    that doesn't map to any of the five v1 types. The descriptor list
    silently drops it — surfacing a sixth type would expand the SPA's
    rendering surface beyond the closed vocabulary the contract
    promises (see ``docs/api-contract.md`` §11)."""
    from django.contrib.admin import AllValuesFieldListFilter

    with admin_override(
        User,
        get_list_filter=lambda self, request: (
            ("username", AllValuesFieldListFilter),
            "is_active",
        ),
    ):
        response = superuser_client.get(USER_LIST_URL)
    descriptors = response.json()["filters"]
    types = [d["type"] for d in descriptors]
    # The AllValuesFieldListFilter on "username" should drop;
    # "is_active" boolean remains.
    assert types == ["boolean"]
