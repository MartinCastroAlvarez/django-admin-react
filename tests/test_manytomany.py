"""Tests for ManyToMany read + write (Issue #55).

``Group.permissions`` is a stock M2M (Group → Permission) and the
default ``GroupAdmin`` exposes it in its form — no override gymnastics.

Wire contract: ``docs/api-contract.md`` §4 (read) + §5.1 / §5.2 (write).
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from django_admin_react.api.serializers import field_type_for


# --------------------------------------------------------------------------- #
# field_type_for                                                              #
# --------------------------------------------------------------------------- #
def test_field_type_for_m2m_is_manytomany() -> None:
    """ManyToMany now maps to ``"manytomany"``, not ``"unsupported"``."""
    field = Group._meta.get_field("permissions")
    assert field_type_for(field) == "manytomany"


# --------------------------------------------------------------------------- #
# Detail read: M2M as [{id, label}, ...]                                      #
# --------------------------------------------------------------------------- #
def _make_permissions() -> list[Permission]:
    """Materialise two distinct permissions to attach to Groups."""
    ct = ContentType.objects.get_for_model(Group)
    p1 = Permission.objects.create(
        codename="dar_test_perm_1",
        name="dar test perm 1",
        content_type=ct,
    )
    p2 = Permission.objects.create(
        codename="dar_test_perm_2",
        name="dar test perm 2",
        content_type=ct,
    )
    return [p1, p2]


@pytest.mark.django_db
def test_detail_serializes_m2m_as_list_of_envelopes(superuser_client: Client) -> None:
    p1, p2 = _make_permissions()
    g = Group.objects.create(name="alpha")
    g.permissions.add(p1, p2)

    response = superuser_client.get(f"/admin-react/api/v1/auth/group/{g.pk}/")
    assert response.status_code == 200
    body = response.json()
    assert "permissions" in body["fields"]
    perms_field = body["fields"]["permissions"]
    assert perms_field["type"] == "manytomany"
    assert perms_field["to"] == {"app_label": "auth", "model_name": "permission"}
    value = perms_field["value"]
    assert isinstance(value, list)
    pks = {entry["id"] for entry in value}
    assert pks == {p1.pk, p2.pk}


# --------------------------------------------------------------------------- #
# Write path: accept [pk1, pk2] and persist via form.save_m2m()               #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_patch_replaces_m2m_set(superuser_client: Client) -> None:
    p1, p2 = _make_permissions()
    g = Group.objects.create(name="alpha")
    g.permissions.add(p1)

    response = superuser_client.patch(
        f"/admin-react/api/v1/auth/group/{g.pk}/",
        data=json.dumps({"permissions": [p2.pk]}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    g.refresh_from_db()
    assert set(g.permissions.values_list("pk", flat=True)) == {p2.pk}


@pytest.mark.django_db
def test_patch_accepts_envelope_form_too(superuser_client: Client) -> None:
    """Clients that echo the read shape back are accepted (envelope unwrap)."""
    p1, p2 = _make_permissions()
    g = Group.objects.create(name="alpha")

    response = superuser_client.patch(
        f"/admin-react/api/v1/auth/group/{g.pk}/",
        data=json.dumps(
            {
                "permissions": [
                    {"id": p1.pk, "label": "p1"},
                    {"id": p2.pk, "label": "p2"},
                ]
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    g.refresh_from_db()
    assert set(g.permissions.values_list("pk", flat=True)) == {p1.pk, p2.pk}


@pytest.mark.django_db
def test_patch_to_empty_list_clears_m2m(superuser_client: Client) -> None:
    p1, _ = _make_permissions()
    g = Group.objects.create(name="alpha")
    g.permissions.add(p1)

    response = superuser_client.patch(
        f"/admin-react/api/v1/auth/group/{g.pk}/",
        data=json.dumps({"permissions": []}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    g.refresh_from_db()
    assert g.permissions.count() == 0


@pytest.mark.django_db
def test_patch_with_unrelated_field_does_not_clear_m2m(
    superuser_client: Client,
) -> None:
    """Partial PATCH that doesn't mention the M2M leaves it intact."""
    p1, _ = _make_permissions()
    g = Group.objects.create(name="alpha")
    g.permissions.add(p1)

    response = superuser_client.patch(
        f"/admin-react/api/v1/auth/group/{g.pk}/",
        data=json.dumps({"name": "alpha-renamed"}),
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    g.refresh_from_db()
    # Crucial: the M2M was NOT cleared by a PATCH that didn't mention it.
    assert set(g.permissions.values_list("pk", flat=True)) == {p1.pk}


@pytest.mark.django_db
def test_merged_initial_raises_on_broken_m2m_descriptor() -> None:
    """Closes #119 / S-CRIT-1: a broken M2M descriptor must NOT fall back to ``[]``.

    The previous implementation wrapped the M2M read in
    ``try/except Exception: merged[name] = []``. If the descriptor
    ever did raise (half-migrated state, broken ``through``, etc.),
    the bare list would flow into ``form.save_m2m()`` during a
    subsequent PATCH and **silently wipe** every existing related
    row. The fix removes the fallback — failures now propagate so
    the caller fails closed (HTTP 500) instead of corrupting data.

    This test simulates a raising descriptor and asserts the
    exception is not swallowed.
    """
    from unittest.mock import patch as mock_patch

    from django_admin_react.api.writes import merged_initial_for_update

    p1, _ = _make_permissions()
    g = Group.objects.create(name="alpha")
    g.permissions.add(p1)

    # Patch the manager's ``all`` to raise — simulates a broken
    # descriptor (e.g. corrupted through-table). With S-CRIT-1
    # patched out, this exception now propagates instead of being
    # swallowed into a wipe-shaped ``[]``.
    class _Boom(Exception):
        pass

    with (
        mock_patch.object(
            type(g.permissions),
            "all",
            side_effect=_Boom("simulated descriptor failure"),
        ),
        pytest.raises(_Boom),
    ):
        merged_initial_for_update(
            obj=g,
            writable=["name", "permissions"],
            payload={"name": "alpha-renamed"},
            model=Group,
        )

    # Belt-and-braces: the descriptor failure must not have wiped
    # the existing M2M as a side effect of the failed read.
    g.refresh_from_db()
    assert set(g.permissions.values_list("pk", flat=True)) == {p1.pk}
