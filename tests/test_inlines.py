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
def test_inline_kind_classified_by_base_class_not_name() -> None:
    """Tabular vs stacked is classified by the inline's *base class*, not
    its subclass name (#417).

    A real-world ``class BookInline(admin.TabularInline)`` has no
    "Tabular" in its name; the old substring check mis-classified it as
    ``stacked`` (a card list instead of a table). ``StackedInline`` —
    whose subclass name likewise need not contain "Stacked" — stays
    ``stacked``.
    """
    from django.contrib.auth.models import Permission

    from django_admin_react.api.inlines import _inline_kind

    class BookInline(TabularInline):  # name has no "Tabular"
        model = Permission
        fk_name = "content_type"

    class NotesInline(StackedInline):  # name has no "Stacked"
        model = Permission
        fk_name = "content_type"

    assert _inline_kind(BookInline(Permission, admin.site)) == "tabular"
    assert _inline_kind(NotesInline(Permission, admin.site)) == "stacked"


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
        rows = _rows_for_inline(inline, ct, "content_type", ["content_type"], request, admin.site)
    finally:
        if added:
            with suppress(Exception):
                admin.site.unregister(ContentType)

    assert len(rows) == 1
    fk = rows[0]["fields"]["content_type"]
    assert fk["to"] == {"app_label": "contenttypes", "model_name": "contenttype"}


@pytest.mark.django_db
def test_inline_show_change_link_gated_on_child_registration() -> None:
    """`show_change_link` is True only when the inline opts in AND the
    child model is admin-registered, so the per-row change link can never
    404 (same closed-vocabulary posture as inline FK targets, #384)."""
    from contextlib import suppress

    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from django.test import RequestFactory

    from django_admin_react.api.inlines import _spec_for_inline

    ct = ContentType.objects.create(app_label="dar_test", model="thing")

    class _LinkedInline(TabularInline):
        model = Permission
        fk_name = "content_type"
        show_change_link = True

    # Inline's parent model is ContentType (Permission.content_type → CT).
    inline = _LinkedInline(ContentType, admin.site)
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="inline-link-su", email="link@example.com", password="x"
    )

    # Child registered → the opt-in is honoured.
    added = Permission not in admin.site._registry
    if added:
        admin.site.register(Permission)
    try:
        spec = _spec_for_inline(inline, ct, request, admin.site)
    finally:
        if added:
            with suppress(Exception):
                admin.site.unregister(Permission)
    assert spec is not None
    assert spec["show_change_link"] is True

    # Child NOT registered → forced False (a link would 404).
    if Permission in admin.site._registry:
        with suppress(Exception):
            admin.site.unregister(Permission)
    spec_unreg = _spec_for_inline(inline, ct, request, admin.site)
    assert spec_unreg is not None
    assert spec_unreg["show_change_link"] is False


@pytest.mark.django_db
def test_inline_spec_carries_child_pk_field() -> None:
    """The inline spec surfaces the child model's pk field name (#418) so
    the SPA can render an explicit (e.g. UUID) pk column without truncation,
    mirroring the list ``pk_field``."""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from django.test import RequestFactory

    from django_admin_react.api.inlines import _spec_for_inline

    ct = ContentType.objects.create(app_label="dar_test_pk", model="thing")

    class _Inline(TabularInline):
        model = Permission
        fk_name = "content_type"

    inline = _Inline(ContentType, admin.site)
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="inline-pk-su", email="pk@example.com", password="x"
    )

    spec = _spec_for_inline(inline, ct, request, admin.site)
    assert spec is not None
    # Permission's pk is the implicit auto "id".
    assert spec["pk_field"] == Permission._meta.pk.name == "id"


@pytest.mark.django_db
def test_inline_show_change_link_gated_on_child_view_permission() -> None:
    """`show_change_link` requires the user's ``has_view_permission`` on the
    CHILD model, not just registration (#301 least-disclosure). A child that
    is registered but unviewable by this user → no link, so the SPA can't
    leak adjacency to a model the detail endpoint would 404/403 on."""
    from contextlib import suppress

    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from django.test import RequestFactory

    from django_admin_react.api.inlines import _spec_for_inline

    ct = ContentType.objects.create(app_label="dar_test", model="thing2")

    class _LinkedInline(TabularInline):
        model = Permission
        fk_name = "content_type"
        show_change_link = True

    inline = _LinkedInline(ContentType, admin.site)
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="inline-noview-su", email="noview@example.com", password="x"
    )

    added = Permission not in admin.site._registry
    if added:
        admin.site.register(Permission)
    child_admin = admin.site._registry[Permission]
    had_own = "has_view_permission" in child_admin.__dict__
    original = child_admin.__dict__.get("has_view_permission")
    try:
        # Registered, but the user is denied view on the child → no link.
        child_admin.has_view_permission = lambda request, obj=None: False
        spec = _spec_for_inline(inline, ct, request, admin.site)
    finally:
        if had_own:
            child_admin.has_view_permission = original
        else:
            with suppress(AttributeError):
                del child_admin.has_view_permission
        if added:
            with suppress(Exception):
                admin.site.unregister(Permission)
    assert spec is not None
    assert spec["show_change_link"] is False
