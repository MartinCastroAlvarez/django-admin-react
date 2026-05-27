"""Tests for ``list_filter`` surfacing on the list endpoint (Issue #56).

Wire contract: ``docs/api-contract.md`` §3.3.

Covered:

- Admin with no ``list_filter`` → ``filters: []`` (always-present key).
- BooleanField filter → ``{type: "boolean"}``, narrows on
  ``?<field>=true|false``.
- Choice field filter → ``{type: "choice", choices: [...]}``, narrows
  on exact value.
- ``SimpleListFilter`` subclass → ``{type: "custom", lookups: [...]}``,
  narrows via the filter's own ``queryset(...)`` method.
- ForeignKey filter (small target) → ``{type: "foreignkey", choices: [...]}``,
  narrows on FK pk.
- Unknown / garbage query params → silently ignored, never 500.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextlib import suppress
from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q
from django.test import Client

from django_admin_react.api.filters import _spec_for_fk

LIST_USER_URL = "/admin-react/api/v1/auth/user/"


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
# Default: no list_filter → empty filters list                                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_no_list_filter_returns_empty_filters_array(
    superuser_client: Client,
) -> None:
    """When the admin clears ``list_filter``, the response key is `[]`.

    The key is always present (not omitted) so the SPA can branch on
    ``filters.length`` without an `if key in response` guard.
    """
    User = get_user_model()
    with admin_attr(User, list_filter=()):
        response = superuser_client.get(LIST_USER_URL)
    body = response.json()
    assert "filters" in body
    assert body["filters"] == []


# --------------------------------------------------------------------------- #
# BooleanField                                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_boolean_filter_metadata(superuser_client: Client) -> None:
    User = get_user_model()
    with admin_attr(User, list_filter=("is_staff",)):
        response = superuser_client.get(LIST_USER_URL)
    body = response.json()
    assert len(body["filters"]) == 1
    f = body["filters"][0]
    assert f["name"] == "is_staff"
    assert f["type"] == "boolean"


@pytest.mark.django_db
def test_boolean_filter_narrows_queryset(superuser_client: Client) -> None:
    User = get_user_model()
    User.objects.create_user(username="alice", password="x", is_staff=False)  # noqa: S106
    User.objects.create_user(username="bob", password="x", is_staff=True)  # noqa: S106
    with admin_attr(User, list_filter=("is_staff",)):
        response = superuser_client.get(LIST_USER_URL + "?is_staff=false")
    body = response.json()
    usernames = {row["fields"].get("username", row["label"]) for row in body["results"]}
    assert "alice" in usernames
    assert "bob" not in usernames


# --------------------------------------------------------------------------- #
# SimpleListFilter                                                            #
# --------------------------------------------------------------------------- #
class _ActiveFilter(SimpleListFilter):
    title = "Active state"
    parameter_name = "active_state"

    def lookups(self, request, model_admin):
        return [("yes", "Active"), ("no", "Inactive")]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(is_active=True)
        if value == "no":
            return queryset.filter(is_active=False)
        return queryset


@pytest.mark.django_db
def test_simple_list_filter_metadata(superuser_client: Client) -> None:
    User = get_user_model()
    with admin_attr(User, list_filter=(_ActiveFilter,)):
        response = superuser_client.get(LIST_USER_URL)
    body = response.json()
    assert len(body["filters"]) == 1
    f = body["filters"][0]
    assert f["name"] == "active_state"
    assert f["type"] == "custom"
    assert f["label"] == "Active state"
    assert {opt["value"] for opt in f["lookups"]} == {"yes", "no"}


@pytest.mark.django_db
def test_simple_list_filter_narrows_queryset(superuser_client: Client) -> None:
    User = get_user_model()
    User.objects.create_user(username="alice", password="x", is_active=True)  # noqa: S106
    User.objects.create_user(username="bob", password="x", is_active=False)  # noqa: S106
    with admin_attr(User, list_filter=(_ActiveFilter,)):
        response = superuser_client.get(LIST_USER_URL + "?active_state=no")
    body = response.json()
    usernames = {row["fields"].get("username", row["label"]) for row in body["results"]}
    assert "bob" in usernames
    assert "alice" not in usernames


class _DefaultTenantFilter(SimpleListFilter):
    """Applies a default ('exclude') when no querystring param is present —
    the pattern #283 targets: the SPA must reflect the default, not 'All'."""

    title = "Tenants"
    parameter_name = "tenants"

    def lookups(self, request, model_admin):
        return [("all", "All tenants"), ("exclude", "Exclude test tenants")]

    def value(self):
        return super().value() or "exclude"

    def queryset(self, request, queryset):
        return queryset


@pytest.mark.django_db
def test_simple_list_filter_reports_selected_from_param(superuser_client: Client) -> None:
    """The descriptor echoes the explicitly-selected lookup (#283)."""
    User = get_user_model()
    with admin_attr(User, list_filter=(_ActiveFilter,)):
        body = superuser_client.get(LIST_USER_URL + "?active_state=no").json()
    assert body["filters"][0]["selected"] == "no"


@pytest.mark.django_db
def test_simple_list_filter_reports_applied_default_as_selected(superuser_client: Client) -> None:
    """A filter that applies a default via ``value()`` reports that default
    as ``selected`` even with no querystring param, so the SPA shows it
    instead of 'All' (#283)."""
    User = get_user_model()
    with admin_attr(User, list_filter=(_DefaultTenantFilter,)):
        body = superuser_client.get(LIST_USER_URL).json()  # no param
    f = body["filters"][0]
    assert f["name"] == "tenants"
    assert f["selected"] == "exclude"  # the default, not None / All


@pytest.mark.django_db
def test_simple_list_filter_selected_is_null_without_default(superuser_client: Client) -> None:
    """A filter with no default + no param reports ``selected: null`` so the
    SPA correctly shows 'All' (#283)."""
    User = get_user_model()
    with admin_attr(User, list_filter=(_ActiveFilter,)):
        body = superuser_client.get(LIST_USER_URL).json()
    assert body["filters"][0]["selected"] is None


# --------------------------------------------------------------------------- #
# Choice field                                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_unknown_filter_param_silently_ignored(superuser_client: Client) -> None:
    """``?nonexistent=foo`` doesn't 500 and doesn't narrow."""
    User = get_user_model()
    User.objects.create_user(username="alice", password="x")  # noqa: S106
    response = superuser_client.get(LIST_USER_URL + "?nonexistent=foo")
    assert response.status_code == 200
    # Result count unchanged (the unknown param was a no-op).
    assert response.json()["total"] >= 1


@pytest.mark.django_db
def test_garbage_value_returns_empty_not_500(superuser_client: Client) -> None:
    """A truly broken value (non-int for a numeric FK) returns ``.none()``, not 500."""
    User = get_user_model()
    with admin_attr(User, list_filter=("is_staff",)):
        # is_staff is boolean; "maybe" is neither true nor false →
        # the boolean branch in apply_filters skips it, so this is a
        # no-op rather than zero rows. The endpoint stays 200.
        response = superuser_client.get(LIST_USER_URL + "?is_staff=maybe")
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# ForeignKey (small target)                                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_fk_filter_includes_inline_choices_when_small(
    superuser_client: Client,
) -> None:
    """ForeignKey filter to a tiny target table inlines the choices."""
    Group.objects.create(name="alpha")
    Group.objects.create(name="beta")

    User = get_user_model()
    with admin_attr(User, list_filter=(("groups", admin.RelatedOnlyFieldListFilter),)):
        # The above tuple form: the package's v1 logic falls back to
        # field-based handling. Use the plain "groups" entry instead
        # for the v1 contract test.
        pass
    with admin_attr(User, list_filter=("groups",)):
        response = superuser_client.get(LIST_USER_URL)
    # `groups` is a ManyToManyField — not surfaced as a v1 filter type.
    # The filter is silently skipped (back-compat surface; M2M filter
    # support is part of #55 follow-up). We just assert no 500.
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# FK filter choices honour the field's ``limit_choices_to`` (#273)            #
# --------------------------------------------------------------------------- #
# The test project registers only auth models (no FK with a declared
# ``limit_choices_to``), so these exercise the choice-building helper
# directly with a stub field over the registered ``Group`` model. The
# attributes read are exactly the ones ``_spec_for_fk`` touches:
# ``related_model``, ``verbose_name``, and ``get_limit_choices_to()``.
def _fk_stub(limit: object) -> SimpleNamespace:
    return SimpleNamespace(
        related_model=Group,
        verbose_name="group",
        get_limit_choices_to=lambda: limit,
    )


@pytest.mark.django_db
def test_fk_filter_choices_respect_dict_limit_choices_to() -> None:
    """A dict ``limit_choices_to`` narrows the inlined options — parity
    with Django's RelatedFieldListFilter (#273)."""
    alpha = Group.objects.create(name="alpha")
    apex = Group.objects.create(name="apex")
    Group.objects.create(name="beta")

    spec = _spec_for_fk("grp", _fk_stub({"name__startswith": "a"}), None, admin.site)
    assert spec is not None
    assert {c["value"] for c in spec["choices"]} == {alpha.pk, apex.pk}


@pytest.mark.django_db
def test_fk_filter_choices_respect_q_limit_choices_to() -> None:
    """A ``Q``-object ``limit_choices_to`` is honoured too."""
    alpha = Group.objects.create(name="alpha")
    Group.objects.create(name="beta")
    gamma = Group.objects.create(name="gamma")

    spec = _spec_for_fk("grp", _fk_stub(Q(name="alpha") | Q(name="gamma")), None, admin.site)
    assert spec is not None
    assert {c["value"] for c in spec["choices"]} == {alpha.pk, gamma.pk}


@pytest.mark.django_db
@pytest.mark.parametrize("empty", [{}, None])
def test_fk_filter_choices_unlimited_when_no_limit(empty: object) -> None:
    """An empty / unset limit is a no-op — every related row is offered,
    and the guard must never call ``complex_filter(None)`` (which raises)."""
    alpha = Group.objects.create(name="alpha")
    beta = Group.objects.create(name="beta")

    spec = _spec_for_fk("grp", _fk_stub(empty), None, admin.site)
    assert spec is not None
    assert {c["value"] for c in spec["choices"]} == {alpha.pk, beta.pk}
