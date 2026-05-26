"""Inline formset write path (Issue #54 write half).

Contract: ``docs/api-contract.md`` §5.4. Implementation:
``django_admin_react/api/inlines_write.py`` + the integration in
``api/views/update.py``.

Test fixture — a real FK parent/child relationship available in every
Django test DB without a custom app: ``contenttypes.ContentType``
(parent) and ``auth.Permission`` (child, ``Permission.content_type`` is
a FK). We register a throwaway ``ContentTypeAdmin`` with a
``PermissionInline`` for the duration of each test.

Covers the Architect's #54 test minimums:
- add / edit / delete a row round-trips through ``formset.save()``;
- a per-row 403 rolls back the WHOLE PATCH (parent change reverted);
- unknown inline key → 400 (deny-by-default, no silent ignore);
- malformed payload shape → 400, not 500.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.admin import TabularInline
from django.contrib.auth.models import Permission  # pylint: disable=imported-auth-user
from django.contrib.contenttypes.models import ContentType
from django.test import Client


class PermissionInline(TabularInline):
    model = Permission
    fk_name = "content_type"
    extra = 0
    fields = ["name", "codename"]


class ContentTypeAdmin(admin.ModelAdmin):
    inlines = [PermissionInline]


@contextmanager
def _ct_admin_registered():
    """Register ContentType with a Permission inline for the test."""
    already = ContentType in admin.site._registry
    if not already:
        admin.site.register(ContentType, ContentTypeAdmin)
    try:
        yield
    finally:
        if not already:
            admin.site.unregister(ContentType)


def _detail_url(ct: ContentType) -> str:
    return f"/admin-react/api/v1/contenttypes/contenttype/{ct.pk}/"


def _new_ct() -> ContentType:
    """A throwaway ContentType row to hang inline Permissions off."""
    return ContentType.objects.create(app_label="dar_test", model="widget")


# --------------------------------------------------------------------------- #
# Add                                                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_add_row_roundtrips(superuser_client: Client) -> None:
    with _ct_admin_registered():
        ct = _new_ct()
        body = {
            "inlines": {
                "content_type_set": {
                    "items": [
                        {"pk": None, "fields": {"name": "Can frobnicate", "codename": "frob"}}
                    ]
                }
            }
        }
        resp = superuser_client.patch(
            _detail_url(ct), data=json.dumps(body), content_type="application/json"
        )
        assert resp.status_code == 200, resp.content
        assert Permission.objects.filter(content_type=ct, codename="frob").exists()


# --------------------------------------------------------------------------- #
# Edit                                                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_edit_row_roundtrips(superuser_client: Client) -> None:
    with _ct_admin_registered():
        ct = _new_ct()
        perm = Permission.objects.create(content_type=ct, name="Old", codename="old")
        body = {
            "inlines": {
                "content_type_set": {
                    "items": [{"pk": perm.pk, "fields": {"name": "New name", "codename": "old"}}]
                }
            }
        }
        resp = superuser_client.patch(
            _detail_url(ct), data=json.dumps(body), content_type="application/json"
        )
        assert resp.status_code == 200, resp.content
        perm.refresh_from_db()
        assert perm.name == "New name"


# --------------------------------------------------------------------------- #
# Delete                                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_delete_row_roundtrips(superuser_client: Client) -> None:
    with _ct_admin_registered():
        ct = _new_ct()
        perm = Permission.objects.create(content_type=ct, name="Doomed", codename="doomed")
        body = {
            "inlines": {
                "content_type_set": {"items": [{"pk": perm.pk, "DELETE": True}]}
            }
        }
        resp = superuser_client.patch(
            _detail_url(ct), data=json.dumps(body), content_type="application/json"
        )
        assert resp.status_code == 200, resp.content
        assert not Permission.objects.filter(pk=perm.pk).exists()


# --------------------------------------------------------------------------- #
# Per-row 403 rolls back the whole PATCH                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_delete_without_permission_rolls_back_parent(superuser_client: Client) -> None:
    """A forbidden DELETE state reverts the parent change too (atomic)."""

    class NoDeleteInline(TabularInline):
        model = Permission
        fk_name = "content_type"
        fields = ["name", "codename"]

        def has_delete_permission(self, request, obj=None):
            return False

    class NoDeleteCTAdmin(admin.ModelAdmin):
        inlines = [NoDeleteInline]

    admin.site.register(ContentType, NoDeleteCTAdmin)
    try:
        ct = _new_ct()
        original_model = ct.model
        perm = Permission.objects.create(content_type=ct, name="Keep", codename="keep")
        body = {
            "model": "changed-parent",  # parent field change that must be reverted
            "inlines": {"content_type_set": {"items": [{"pk": perm.pk, "DELETE": True}]}},
        }
        resp = superuser_client.patch(
            _detail_url(ct), data=json.dumps(body), content_type="application/json"
        )
        assert resp.status_code == 403, resp.content
        # The child still exists (delete rolled back)...
        assert Permission.objects.filter(pk=perm.pk).exists()
        # ...and the parent field change rolled back too (atomic).
        ct.refresh_from_db()
        assert ct.model == original_model
    finally:
        admin.site.unregister(ContentType)


# --------------------------------------------------------------------------- #
# Deny-by-default + malformed shape                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_unknown_inline_key_is_400(superuser_client: Client) -> None:
    with _ct_admin_registered():
        ct = _new_ct()
        body = {"inlines": {"nonexistent_set": {"items": [{"pk": None, "fields": {}}]}}}
        resp = superuser_client.patch(
            _detail_url(ct), data=json.dumps(body), content_type="application/json"
        )
        assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_malformed_inline_items_is_400(superuser_client: Client) -> None:
    with _ct_admin_registered():
        ct = _new_ct()
        body = {"inlines": {"content_type_set": {"items": "not-a-list"}}}
        resp = superuser_client.patch(
            _detail_url(ct), data=json.dumps(body), content_type="application/json"
        )
        assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_invalid_formset_data_is_400_no_persist(superuser_client: Client) -> None:
    """A formset validation failure (missing required field) → 400, no row."""
    with _ct_admin_registered():
        ct = _new_ct()
        before = Permission.objects.filter(content_type=ct).count()
        body = {
            "inlines": {
                # ``name`` is required on Permission; omit it.
                "content_type_set": {"items": [{"pk": None, "fields": {"codename": "x"}}]}
            }
        }
        resp = superuser_client.patch(
            _detail_url(ct), data=json.dumps(body), content_type="application/json"
        )
        assert resp.status_code == 400, resp.content
        assert Permission.objects.filter(content_type=ct).count() == before
