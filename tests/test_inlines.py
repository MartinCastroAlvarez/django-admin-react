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


# --------------------------------------------------------------------------- #
# Inline rows: display methods on the inline admin resolve (the "—" bug)       #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_inline_row_resolves_admin_display_method() -> None:
    """An inline row column that is a display method defined on the inline
    admin (the ``@admin.display def x(self, obj)`` pattern, called with
    ``obj``) must resolve to the method's return value — not ``None`` /
    "—".

    Mirrors the detail-view fix in #232: row values resolve through
    Django's own ``lookup_field(name, obj, inline)`` (admin-first), so a
    method living on the *inline admin* resolves, not just methods on the
    model instance. A naive ``getattr(obj, name)`` returns ``None`` for
    admin methods, which the SPA renders as a dash for every row.
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from django.test import RequestFactory

    from django_admin_react.api.inlines import _rows_for_inline

    ct = ContentType.objects.create(app_label="dar_test", model="widget")
    Permission.objects.create(content_type=ct, codename="can_do", name="Can do")

    class _PermInline(TabularInline):
        model = Permission
        fk_name = "content_type"

        def shout(self, obj):  # bound on the admin; called with obj
            return f"shout-{obj.codename}"

    inline = _PermInline(Permission, admin.site)
    # The inline's get_queryset runs a view/change permission check, which
    # reads request.user — attach a superuser so the rows are visible.
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="inline-su", email="su@example.com", password="x"
    )

    rows = _rows_for_inline(inline, ct, "content_type", ["codename", "shout"], request)

    assert len(rows) == 1
    fields = rows[0]["fields"]
    # The real model field keeps resolving.
    assert fields["codename"] == "can_do"
    # The admin display method resolves to its return value (was None
    # before the fix → rendered as "—").
    assert fields["shout"] == "shout-can_do"


@pytest.mark.django_db
def test_inline_row_fk_carries_navigation_target() -> None:
    """An inline row's ForeignKey column carries the ``to`` navigation
    envelope when its target model is admin-registered, so inline FK cells
    are clickable (parity with list/detail FK cells). Regression: inlines
    omitted ``admin_site`` when serializing FK values, so ``to`` was never
    emitted (#270)."""
    from contextlib import suppress

    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from django.test import RequestFactory

    from django_admin_react.api.inlines import _rows_for_inline

    ct = ContentType.objects.create(app_label="dar_test", model="gadget")
    Permission.objects.create(content_type=ct, codename="poke", name="Poke")

    class _PermInline(TabularInline):
        model = Permission
        fk_name = "content_type"

    inline = _PermInline(Permission, admin.site)
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="inline-fk-su", email="fk@example.com", password="x"
    )

    # Register the FK target so `to` is emitted; clean up afterwards.
    if ContentType not in admin.site._registry:
        admin.site.register(ContentType)
        added = True
    else:
        added = False
    try:
        rows = _rows_for_inline(
            inline, ct, "content_type", ["content_type"], request, admin.site
        )
    finally:
        if added:
            with suppress(Exception):
                admin.site.unregister(ContentType)

    assert len(rows) == 1
    fk = rows[0]["fields"]["content_type"]
    assert fk["to"] == {"app_label": "contenttypes", "model_name": "contenttype"}


# --------------------------------------------------------------------------- #
# show_change_link (#384): per-row link to the child's own change page         #
# --------------------------------------------------------------------------- #
@contextmanager
def _registered(model_cls):
    """Temporarily register ``model_cls`` on the admin site, if needed."""
    added = model_cls not in admin.site._registry
    if added:
        admin.site.register(model_cls)
    try:
        yield
    finally:
        if added:
            with suppress(Exception):
                admin.site.unregister(model_cls)


def _superuser_request():
    from django.contrib.auth import get_user_model
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="scl-su", email="scl@example.com", password="x"
    )
    return request


@pytest.mark.django_db
def test_inline_show_change_link_emitted_when_opted_in_and_viewable() -> None:
    """When the inline sets ``show_change_link`` and the child model is
    registered + viewable, the descriptor carries ``show_change_link`` plus
    the child's ``change_link_to`` routing envelope (#384)."""
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    from django_admin_react.api.inlines import _spec_for_inline

    ct = ContentType.objects.create(app_label="dar_test", model="linky")

    class _PermInline(TabularInline):
        model = Permission
        fk_name = "content_type"
        show_change_link = True

    # Parent model is ContentType — the model the child's ``content_type``
    # FK points back to (so ``get_fields`` can build the inline formset).
    inline = _PermInline(ContentType, admin.site)
    request = _superuser_request()

    with _registered(Permission):
        spec = _spec_for_inline(inline, ct, request, admin.site)

    assert spec is not None
    assert spec["show_change_link"] is True
    assert spec["change_link_to"] == {"app_label": "auth", "model_name": "permission"}


@pytest.mark.django_db
def test_inline_show_change_link_absent_when_not_opted_in() -> None:
    """Without ``show_change_link`` the descriptor omits both keys, even when
    the child model is registered + viewable."""
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    from django_admin_react.api.inlines import _spec_for_inline

    ct = ContentType.objects.create(app_label="dar_test", model="nolink")

    class _PermInline(TabularInline):
        model = Permission
        fk_name = "content_type"

    inline = _PermInline(ContentType, admin.site)
    request = _superuser_request()

    with _registered(Permission):
        spec = _spec_for_inline(inline, ct, request, admin.site)

    assert spec is not None
    assert "show_change_link" not in spec
    assert "change_link_to" not in spec


@pytest.mark.django_db
def test_inline_show_change_link_gated_on_registration() -> None:
    """``show_change_link`` is suppressed when the child model is *not*
    registered on the admin site — we never advertise a link the detail
    endpoint would 404 on (same gate as the FK ``to`` envelope, #301)."""
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    from django_admin_react.api.inlines import _spec_for_inline

    ct = ContentType.objects.create(app_label="dar_test", model="unreg")

    class _PermInline(TabularInline):
        model = Permission
        fk_name = "content_type"
        show_change_link = True

    inline = _PermInline(ContentType, admin.site)
    request = _superuser_request()

    # Ensure Permission is unregistered for the duration of this assertion.
    was_registered = Permission in admin.site._registry
    if was_registered:
        admin.site.unregister(Permission)
    try:
        spec = _spec_for_inline(inline, ct, request, admin.site)
    finally:
        if was_registered:
            admin.site.register(Permission)

    assert spec is not None
    assert "show_change_link" not in spec
    assert "change_link_to" not in spec
