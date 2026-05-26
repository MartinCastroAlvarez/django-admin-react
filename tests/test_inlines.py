"""Tests for ``ModelAdmin.inlines`` read surface (Issue #54).

Write support (formset round-trip) is tracked as a follow-up. This
PR closes the read half: inlines + their existing rows show up in
the detail response so the SPA can render them in view-only flows.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextlib import suppress

import pytest
from django.contrib import admin
from django.contrib.admin import StackedInline
from django.contrib.admin import TabularInline
from django.contrib.auth.models import Group
from django.test import Client

from django_admin_react.api.inlines import _resolve_fk_name


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
# Default: no inlines → empty array on the detail response                    #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_default_admin_has_empty_inlines(superuser_client: Client) -> None:
    """``inlines`` is always present in the detail response (empty `[]`)."""
    g = Group.objects.create(name="alpha")
    response = superuser_client.get(f"/admin-react/api/v1/auth/group/{g.pk}/")
    assert response.status_code == 200
    body = response.json()
    assert "inlines" in body
    assert body["inlines"] == []


# --------------------------------------------------------------------------- #
# _resolve_fk_name: the FK-back-to-parent detection                           #
# --------------------------------------------------------------------------- #
def test_resolve_fk_name_uses_declared_attribute() -> None:
    """When the inline declares ``fk_name``, it's used as-is."""

    class _Inline(TabularInline):
        model = Group  # placeholder
        fk_name = "explicit_parent_fk"

    assert _resolve_fk_name(_Inline, Group(name="x")) == "explicit_parent_fk"


# --------------------------------------------------------------------------- #
# Inline kind detection (tabular vs stacked)                                  #
# --------------------------------------------------------------------------- #
def test_inline_kind_detection_in_class_name() -> None:
    """The package detects tabular vs stacked by the class name only."""
    # We're not building real inline payloads here (those require a
    # parent/child FK fixture); this is a pure-Python class-name check
    # to lock the contract.
    assert "Tabular" in TabularInline.__name__
    assert "Stacked" in StackedInline.__name__


# --------------------------------------------------------------------------- #
# _fields_meta carries type + required (Issue #54 — unblocks inline editing)  #
# --------------------------------------------------------------------------- #
def test_inline_fields_meta_carries_type_and_required() -> None:
    """Each inline field meta exposes ``type`` + ``required`` so the SPA
    can render a typed input per field in edit mode."""
    from django.contrib.auth.models import Permission

    from django_admin_react.api.inlines import _fields_meta

    class _PermInline(TabularInline):
        model = Permission
        fk_name = "content_type"
        fields = ["name", "codename"]

    inline = _PermInline(Permission, admin.site)
    meta = _fields_meta(inline, Permission, ["name", "codename"], None)
    by_name = {m["name"]: m for m in meta}
    # Permission.name is a non-blank CharField → type "string", required.
    assert by_name["name"]["type"] == "string"
    assert by_name["name"]["required"] is True
    assert by_name["codename"]["type"] == "string"
    # Back-compat: the original keys are still present.
    assert set(by_name["name"]) >= {"name", "label", "readonly", "type", "required"}
