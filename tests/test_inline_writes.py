"""Tests for the inline formset **write** half (Issue #54).

The read half (``inlines.py``) surfaces inlines + rows on the detail
response; this exercises the create/update write path that round-trips
inline edits through Django's own inline formset machinery.

Fixture: a ``ContentType`` parent with a ``PermissionInline`` child
(``Permission.content_type`` is the FK back to ``ContentType``). This
uses only Django built-ins — no test-app models / migrations.

Every test asserts the **actual DB state** after the write, so a
subtly-wrong JSON→formset translation (the data-corruption risk this
feature carries) is caught here rather than in production.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin import TabularInline
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client


class _PermissionInline(TabularInline):
    model = Permission
    fk_name = "content_type"
    fields = ["name", "codename"]
    extra = 0


class _ContentTypeAdmin(ModelAdmin):
    inlines = [_PermissionInline]


@contextmanager
def _ct_admin_with_inline(inline_cls=_PermissionInline):
    """Register ContentType with a Permission inline for the test."""

    class _Admin(ModelAdmin):
        inlines = [inline_cls]

    if ContentType in admin.site._registry:
        admin.site.unregister(ContentType)
    admin.site.register(ContentType, _Admin)
    try:
        yield
    finally:
        admin.site.unregister(ContentType)


def _detail_url(ct: ContentType) -> str:
    return f"/admin-react/api/v1/contenttypes/contenttype/{ct.pk}/"


def _patch(client: Client, url: str, body: dict) -> object:
    return client.patch(url, data=json.dumps(body), content_type="application/json")


def _inline_name(client: Client, ct: ContentType) -> str:
    """Read the inline's wire ``name`` from the detail response, so the
    write uses the exact key the SPA received."""
    body = client.get(_detail_url(ct)).json()
    assert body["inlines"], "expected at least one inline descriptor"
    return body["inlines"][0]["name"]


# --------------------------------------------------------------------------- #
# Create a child via an inline row                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_add_creates_child_under_parent(superuser_client: Client) -> None:
    with _ct_admin_with_inline():
        ct = ContentType.objects.create(app_label="dartest", model="widget")
        name = _inline_name(superuser_client, ct)
        before = Permission.objects.filter(content_type=ct).count()

        resp = _patch(
            superuser_client,
            _detail_url(ct),
            {"inlines": {name: [{"name": "Can frobnicate", "codename": "frob_widget"}]}},
        )
        assert resp.status_code == 200

        created = Permission.objects.filter(content_type=ct, codename="frob_widget")
        assert created.count() == 1
        assert Permission.objects.filter(content_type=ct).count() == before + 1
        assert created.first().name == "Can frobnicate"


# --------------------------------------------------------------------------- #
# Update an existing child                                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_change_updates_existing_child(superuser_client: Client) -> None:
    with _ct_admin_with_inline():
        ct = ContentType.objects.create(app_label="dartest", model="gadget")
        perm = Permission.objects.create(content_type=ct, name="Old name", codename="gadget_op")
        name = _inline_name(superuser_client, ct)

        resp = _patch(
            superuser_client,
            _detail_url(ct),
            {"inlines": {name: [{"id": perm.pk, "name": "New name", "codename": "gadget_op"}]}},
        )
        assert resp.status_code == 200

        perm.refresh_from_db()
        assert perm.name == "New name"
        # No extra row created.
        assert Permission.objects.filter(content_type=ct).count() == 1


# --------------------------------------------------------------------------- #
# Delete an existing child                                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_delete_removes_child(superuser_client: Client) -> None:
    with _ct_admin_with_inline():
        ct = ContentType.objects.create(app_label="dartest", model="sprocket")
        perm = Permission.objects.create(content_type=ct, name="Doomed", codename="sprocket_doom")
        name = _inline_name(superuser_client, ct)

        resp = _patch(
            superuser_client,
            _detail_url(ct),
            {"inlines": {name: [{"id": perm.pk, "DELETE": True}]}},
        )
        assert resp.status_code == 200
        assert not Permission.objects.filter(pk=perm.pk).exists()


# --------------------------------------------------------------------------- #
# SECURITY: cross-parent id is rejected (no reparenting)                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_rejects_cross_parent_id(superuser_client: Client) -> None:
    """An ``id`` that belongs to a *different* parent's child must be
    rejected — the SPA can't re-parent or edit a sibling-tree row by
    guessing a pk."""
    with _ct_admin_with_inline():
        ct_a = ContentType.objects.create(app_label="dartest", model="alpha")
        ct_b = ContentType.objects.create(app_label="dartest", model="beta")
        perm_b = Permission.objects.create(content_type=ct_b, name="B perm", codename="beta_perm")
        name = _inline_name(superuser_client, ct_a)

        resp = _patch(
            superuser_client,
            _detail_url(ct_a),
            {"inlines": {name: [{"id": perm_b.pk, "name": "Hijacked", "codename": "beta_perm"}]}},
        )
        assert resp.status_code == 403
        # perm_b is untouched + still under ct_b.
        perm_b.refresh_from_db()
        assert perm_b.name == "B perm"
        assert perm_b.content_type_id == ct_b.pk


# --------------------------------------------------------------------------- #
# SECURITY: per-operation permission gating                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_add_forbidden_without_add_permission(superuser_client: Client) -> None:
    class _NoAddInline(TabularInline):
        model = Permission
        fk_name = "content_type"
        fields = ["name", "codename"]
        extra = 0

        def has_add_permission(self, request, obj=None) -> bool:  # noqa: ARG002
            return False

    with _ct_admin_with_inline(inline_cls=_NoAddInline):
        ct = ContentType.objects.create(app_label="dartest", model="locked")
        name = _inline_name(superuser_client, ct)

        resp = _patch(
            superuser_client,
            _detail_url(ct),
            {"inlines": {name: [{"name": "Nope", "codename": "locked_nope"}]}},
        )
        assert resp.status_code == 403
        assert not Permission.objects.filter(content_type=ct, codename="locked_nope").exists()


# --------------------------------------------------------------------------- #
# Invalid inline data → 400, nothing written                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_validation_error_rolls_back(superuser_client: Client) -> None:
    """A row that fails the child form's validation (codename too long)
    returns 400 and writes nothing — parent + inlines are atomic."""
    with _ct_admin_with_inline():
        ct = ContentType.objects.create(app_label="dartest", model="atomic")
        name = _inline_name(superuser_client, ct)
        too_long = "x" * 200  # Permission.codename max_length is 100.

        resp = _patch(
            superuser_client,
            _detail_url(ct),
            {"inlines": {name: [{"name": "Bad", "codename": too_long}]}},
        )
        assert resp.status_code == 400
        assert Permission.objects.filter(content_type=ct).count() == 0


# --------------------------------------------------------------------------- #
# Unknown inline name → 400                                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_unknown_inline_name_rejected(superuser_client: Client) -> None:
    with _ct_admin_with_inline():
        ct = ContentType.objects.create(app_label="dartest", model="unknown")
        resp = _patch(
            superuser_client,
            _detail_url(ct),
            {"inlines": {"not_a_real_inline": [{"name": "x", "codename": "y"}]}},
        )
        assert resp.status_code == 400
