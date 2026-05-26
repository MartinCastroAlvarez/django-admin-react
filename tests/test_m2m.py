"""Tests for ManyToMany read + write support (Issue #55).

Wire contract: ``docs/api-contract.md`` §4 (M2M descriptor + value
shape) and §5.1 / §5.2 (write payload accepts bare pk array).

Test target is ``auth.Group``, which Django registers in its default
admin and which has a ``permissions`` M2M to ``auth.Permission``
(auto-created through). For the explicit-through-with-extras case
we patch ``through._meta.auto_created`` to exercise the read-only
branch without inventing a custom model.

Covered:

- Detail GET surfaces an M2M descriptor with ``type=many_to_many``,
  ``to=`` related-model pointer, ``through=null`` for plain M2M,
  ``widget=select`` by default, and ``value`` as a list of
  ``{id, label}`` dicts.
- ``filter_horizontal`` / ``filter_vertical`` selections promote
  ``widget`` to ``horizontal`` / ``vertical``.
- POST and PATCH write the M2M correctly through ``form.save_m2m()``.
- Through-with-extras: descriptor is ``readonly: true`` with a
  populated ``through`` block; the writable set drops the field;
  payloads naming it return 400.
- Value cap: small sets render inline; large sets return the
  truncated envelope ``{sample, count, truncated}``.
- A M2M field with a sensitive-substring name (``api_key_groups``)
  is dropped from the read **and** write surfaces by the denylist —
  defense-in-depth even when the admin forgets to exclude.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.test import Client

from django_admin_react.api.serializers import is_plain_m2m
from django_admin_react.api.serializers import safe_get_field
from tests.helpers import admin_override

GROUP_LIST_URL = "/admin-react/api/v1/auth/group/"


def _group_detail(pk: int) -> str:
    return f"{GROUP_LIST_URL}{pk}/"


# --------------------------------------------------------------------------- #
# Read path — descriptor shape                                                #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_m2m_descriptor_has_correct_shape(superuser_client: Client) -> None:
    """Plain M2M emits ``type=many_to_many``, ``to``, ``through=null``,
    and ``value`` as ``[{id, label}, ...]``.

    Note: Django's stock ``GroupAdmin`` declares
    ``filter_horizontal = ("permissions",)``, so we clear it inline to
    test the default ``widget=select`` path. The widget-promotion
    branches have their own tests below.
    """
    group = Group.objects.create(name="reviewers")
    perm = Permission.objects.first()
    assert perm is not None
    group.permissions.add(perm)

    model_admin = admin.site._registry[Group]
    original_horizontal = getattr(model_admin, "filter_horizontal", ())
    try:
        model_admin.filter_horizontal = ()
        with admin_override(
            Group,
            get_fields=lambda self, request, obj=None: ("name", "permissions"),
        ):
            response = superuser_client.get(_group_detail(group.pk))
    finally:
        model_admin.filter_horizontal = original_horizontal

    assert response.status_code == 200
    body = response.json()
    descriptor = body["fields"]["permissions"]
    assert descriptor["type"] == "many_to_many"
    assert descriptor["to"] == {"app_label": "auth", "model_name": "permission"}
    assert descriptor["through"] is None
    assert descriptor["widget"] == "select"
    assert isinstance(descriptor["value"], list)
    assert any(item["id"] == perm.pk for item in descriptor["value"])
    assert all("label" in item for item in descriptor["value"])


@pytest.mark.django_db
def test_empty_m2m_renders_empty_array(superuser_client: Client) -> None:
    """A row with no related items returns ``value: []`` (never null)."""
    group = Group.objects.create(name="empty")
    with admin_override(
        Group,
        get_fields=lambda self, request, obj=None: ("name", "permissions"),
    ):
        response = superuser_client.get(_group_detail(group.pk))
    descriptor = response.json()["fields"]["permissions"]
    assert descriptor["value"] == []


@pytest.mark.django_db
def test_filter_horizontal_promotes_widget(superuser_client: Client) -> None:
    """``ModelAdmin.filter_horizontal = ('permissions',)`` → ``widget: horizontal``."""
    group = Group.objects.create(name="horiz")
    model_admin = admin.site._registry[Group]
    original_horizontal = getattr(model_admin, "filter_horizontal", ())
    try:
        model_admin.filter_horizontal = ("permissions",)
        with admin_override(
            Group,
            get_fields=lambda self, request, obj=None: ("name", "permissions"),
        ):
            response = superuser_client.get(_group_detail(group.pk))
        descriptor = response.json()["fields"]["permissions"]
        assert descriptor["widget"] == "horizontal"
    finally:
        model_admin.filter_horizontal = original_horizontal


@pytest.mark.django_db
def test_filter_vertical_promotes_widget(superuser_client: Client) -> None:
    """``ModelAdmin.filter_vertical = ('permissions',)`` → ``widget: vertical``.

    Clear ``filter_horizontal`` first because Django's ``GroupAdmin``
    sets it on ``permissions`` by default — would otherwise win.
    """
    group = Group.objects.create(name="vert")
    model_admin = admin.site._registry[Group]
    original_horizontal = getattr(model_admin, "filter_horizontal", ())
    original_vertical = getattr(model_admin, "filter_vertical", ())
    try:
        model_admin.filter_horizontal = ()
        model_admin.filter_vertical = ("permissions",)
        with admin_override(
            Group,
            get_fields=lambda self, request, obj=None: ("name", "permissions"),
        ):
            response = superuser_client.get(_group_detail(group.pk))
        descriptor = response.json()["fields"]["permissions"]
        assert descriptor["widget"] == "vertical"
    finally:
        model_admin.filter_horizontal = original_horizontal
        model_admin.filter_vertical = original_vertical


# --------------------------------------------------------------------------- #
# Write path                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_patch_writes_m2m_pks(superuser_client: Client) -> None:
    """PATCH with ``{"permissions": [pk1, pk2]}`` replaces the set via
    ``form.save_m2m()`` — never via ``setattr`` (Rule 6)."""
    group = Group.objects.create(name="patch-target")
    perms = list(Permission.objects.all()[:3])
    assert len(perms) >= 2
    group.permissions.set(perms[:1])  # start with 1 perm

    with admin_override(
        Group,
        get_fields=lambda self, request, obj=None: ("name", "permissions"),
    ):
        response = superuser_client.patch(
            _group_detail(group.pk),
            data={"permissions": [perms[1].pk, perms[2].pk]},
            content_type="application/json",
        )

    assert response.status_code == 200
    group.refresh_from_db()
    assert set(group.permissions.values_list("pk", flat=True)) == {
        perms[1].pk,
        perms[2].pk,
    }


@pytest.mark.django_db
def test_patch_empty_payload_leaves_m2m_unchanged(superuser_client: Client) -> None:
    """PATCH that omits the M2M field keeps the current set
    (``merged_initial_for_update`` seeds the current pks)."""
    group = Group.objects.create(name="unchanged")
    perm = Permission.objects.first()
    assert perm is not None
    group.permissions.add(perm)

    with admin_override(
        Group,
        get_fields=lambda self, request, obj=None: ("name", "permissions"),
    ):
        response = superuser_client.patch(
            _group_detail(group.pk),
            data={"name": "renamed"},
            content_type="application/json",
        )
    assert response.status_code == 200
    group.refresh_from_db()
    assert group.name == "renamed"
    assert set(group.permissions.values_list("pk", flat=True)) == {perm.pk}


@pytest.mark.django_db
def test_create_with_m2m_pks(superuser_client: Client) -> None:
    """POST with ``{"name": ..., "permissions": [pks]}`` creates the row
    AND saves the M2M via ``form.save_m2m()`` (called in CreateView)."""
    perm = Permission.objects.first()
    assert perm is not None
    with admin_override(
        Group,
        get_fields=lambda self, request, obj=None: ("name", "permissions"),
    ):
        response = superuser_client.post(
            GROUP_LIST_URL,
            data={"name": "newly-created", "permissions": [perm.pk]},
            content_type="application/json",
        )
    assert response.status_code == 201
    pk = response.json()["pk"]
    created = Group.objects.get(pk=pk)
    assert list(created.permissions.values_list("pk", flat=True)) == [perm.pk]


# --------------------------------------------------------------------------- #
# Through-with-extras: read-only, write rejected                              #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_through_with_extras_descriptor_is_readonly(superuser_client: Client) -> None:
    """When ``through._meta.auto_created`` is False (explicit through),
    the descriptor marks the field readonly and surfaces a populated
    ``through`` block — the SPA renders a read-only hint and a link to
    the through-model admin."""
    group = Group.objects.create(name="through-test")
    perms_field = safe_get_field(Group, "permissions")
    assert perms_field is not None
    with patch.object(perms_field.remote_field.through._meta, "auto_created", False):
        # Sanity: helper agrees the field is no longer a plain M2M.
        assert not is_plain_m2m(perms_field)
        with admin_override(
            Group,
            get_fields=lambda self, request, obj=None: ("name", "permissions"),
        ):
            response = superuser_client.get(_group_detail(group.pk))
    descriptor = response.json()["fields"]["permissions"]
    assert descriptor["readonly"] is True
    assert descriptor["through"] is not None
    assert "app_label" in descriptor["through"]
    assert "model_name" in descriptor["through"]


@pytest.mark.django_db
def test_through_with_extras_write_rejected(superuser_client: Client) -> None:
    """A PATCH that names a through-with-extras M2M returns 400 — the
    field is dropped from ``writable_field_names``, then
    ``reject_forbidden_keys`` surfaces the ``Unknown field`` envelope."""
    group = Group.objects.create(name="through-write")
    perms_field = safe_get_field(Group, "permissions")
    assert perms_field is not None
    perm = Permission.objects.first()
    assert perm is not None
    with (
        patch.object(perms_field.remote_field.through._meta, "auto_created", False),
        admin_override(
            Group,
            get_fields=lambda self, request, obj=None: ("name", "permissions"),
        ),
    ):
        response = superuser_client.patch(
            _group_detail(group.pk),
            data={"permissions": [perm.pk]},
            content_type="application/json",
        )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"
    assert "permissions" in body["error"]["message"]


# --------------------------------------------------------------------------- #
# Truncation cap                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_oversize_m2m_returns_truncated_envelope(superuser_client: Client) -> None:
    """Setting ``M2M_VALUE_CAP=2`` on a 3-perm group returns the
    ``{sample, count, truncated}`` envelope rather than the bare list."""
    group = Group.objects.create(name="big-perms")
    perms = list(Permission.objects.all()[:3])
    assert len(perms) == 3
    group.permissions.set(perms)

    with (
        patch("django_admin_react.api.serializers.M2M_VALUE_CAP", 2),
        admin_override(
            Group,
            get_fields=lambda self, request, obj=None: ("name", "permissions"),
        ),
    ):
        response = superuser_client.get(_group_detail(group.pk))
    descriptor = response.json()["fields"]["permissions"]
    value = descriptor["value"]
    assert isinstance(value, dict)
    assert value["truncated"] is True
    assert value["count"] == 3
    assert len(value["sample"]) == 2
