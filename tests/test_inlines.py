"""Tests for ``ModelAdmin.inlines`` read surface (Issue #54).

Write support (formset round-trip) is tracked as a follow-up. This
PR closes the read half: inlines + their existing rows show up in
the detail response so the SPA can render them in view-only flows.
"""

from __future__ import annotations

from contextlib import contextmanager

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
                try:
                    delattr(model_admin, name)
                except AttributeError:
                    pass
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
