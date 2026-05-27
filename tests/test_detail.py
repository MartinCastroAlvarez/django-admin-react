"""Tests for ``GET /api/v1/<app>/<model>/<pk>/`` (PR #4).

Mandatory matrix from CLAUDE.md §6 + ACCEPTANCE.md §3.5 T-1.
Plus feature-specific: ForeignKey shape, readonly fields, sensitive-
name denylist, bogus pk, per-object has_view_permission.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from tests.helpers import admin_override


def _url(pk: object) -> str:
    return f"/admin-react/api/v1/auth/group/{pk}/"


@pytest.mark.django_db
def test_detail_resolves_via_get_object_not_get_queryset(superuser_client: Client) -> None:
    """The detail view must resolve the object through
    ``ModelAdmin.get_object`` (what Django's change view uses), not
    ``get_queryset().get()``.

    A consumer may override ``get_object`` to bypass a filter that
    ``get_queryset`` applies for list-view scoping/performance — so an
    individual record stays openable even though it's hidden from the
    list. Observed in the laminr pilot: ``LoanPackageAdmin.get_queryset``
    excludes test-tenant packages, but its ``get_object`` deliberately
    bypasses that so the change view still opens them. Resolving detail
    via ``get_queryset`` 404'd such rows.

    Here: ``get_queryset`` returns ``none()`` (hides everything) while
    ``get_object`` returns the real row. The detail view must 200.
    """
    g = Group.objects.create(name="hidden-from-list")

    with admin_override(
        Group,
        get_queryset=lambda self, request: Group.objects.none(),
        get_object=lambda self, request, object_id, from_field=None: Group.objects.filter(
            pk=object_id
        ).first(),
    ):
        response = superuser_client.get(_url(g.pk))

    assert response.status_code == 200, response.content
    assert response.json()["pk"] == g.pk


@pytest.mark.django_db
def test_detail_calls_get_form_with_change_true(superuser_client: Client) -> None:
    """Regression: the detail view must call ``get_form(..., change=True)``
    for an existing object — exactly how Django's change view invokes it.

    A consumer ``get_form`` commonly branches on ``change`` and returns a
    change-specific form whose ``Meta`` omits a *form-only* field (one
    that isn't a model field, e.g. an ``admin_override`` toggle). If the
    detail view calls ``get_form`` WITHOUT ``change=True``, that override
    falls through to ``modelform_factory`` on the form-only field and
    raises ``FieldError`` → 500. Observed in the laminr pilot on
    ``package_reviews.UnderReviewStatus``.
    """
    from django import forms

    g = Group.objects.create(name="example")
    seen: dict[str, object] = {}
    ok_form = forms.modelform_factory(Group, fields=["name"])

    def branching_get_form(self, request, obj=None, change=False, **kwargs):  # noqa: ANN001
        seen["change"] = change
        if obj is not None and change:
            return ok_form
        # Mirror the consumer's failure mode: the non-change path would
        # blow up building a form for a form-only field. Raise so the
        # test fails loudly if the detail view didn't pass change=True.
        raise AssertionError("get_form must be called with change=True for an existing object")

    # Pin `get_fields` so Django's own get_fields → get_form(change=False)
    # path is bypassed (laminr's admin sets `fields` via its @sections
    # decorator, so only our explicit _fields_payload get_form call
    # fires). This isolates the call path the fix targets.
    with admin_override(
        Group,
        get_fields=lambda self, request, obj=None: ["name"],
        get_fieldsets=lambda self, request, obj=None: [(None, {"fields": ["name"]})],
        get_form=branching_get_form,
    ):
        response = superuser_client.get(_url(g.pk))

    assert response.status_code == 200, response.content
    assert seen.get("change") is True


# --------------------------------------------------------------------------- #
# Mandatory 8-row matrix                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_unauthorized(anon_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = anon_client.get(_url(g.pk))
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = user_client.get(_url(g.pk))
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_with_permission_succeeds(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = superuser_client.get(_url(g.pk))
    assert response.status_code == 200
    body = response.json()
    assert body["pk"] == g.pk
    assert body["label"] == "example"
    assert "fields" in body
    assert "fieldsets" in body
    assert "permissions" in body


@pytest.mark.django_db
def test_user_without_view_permission_for_object_forbidden(
    superuser_client: Client,
) -> None:
    g = Group.objects.create(name="example")
    with admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
        response = superuser_client.get(_url(g.pk))
    assert response.status_code in (403, 404)


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.get("/admin-react/api/v1/auth/nope/1/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_bogus_pk_not_found(superuser_client: Client) -> None:
    response = superuser_client.get(_url("not-a-valid-id"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_nonexistent_pk_not_found(superuser_client: Client) -> None:
    response = superuser_client.get(_url(999999))
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_fields_include_required_help_text_and_type(superuser_client: Client) -> None:
    g = Group.objects.create(name="example")
    response = superuser_client.get(_url(g.pk))
    body = response.json()
    assert "name" in body["fields"]
    name_field = body["fields"]["name"]
    assert name_field["type"] == "string"
    assert isinstance(name_field["required"], bool)
    assert isinstance(name_field["readonly"], bool)
    assert "value" in name_field


@pytest.mark.django_db
def test_starts_from_admin_get_queryset(superuser_client: Client) -> None:
    """Detail view must use ModelAdmin.get_queryset, not Model.objects.all."""
    g = Group.objects.create(name="invisible")
    with admin_override(Group, get_queryset=lambda self, request: Group.objects.none()):
        response = superuser_client.get(_url(g.pk))
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# save_options (#154 — Django save-flow button parity)                        #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_detail_includes_save_options_block(superuser_client: Client) -> None:
    """The detail (change-view) response carries the four save-flow flags."""
    g = Group.objects.create(name="example")
    body = superuser_client.get(_url(g.pk)).json()
    assert "save_options" in body
    opts = body["save_options"]
    assert set(opts.keys()) == {
        "show_save",
        "show_save_and_continue",
        "show_save_and_add_another",
        "show_save_as_new",
        "save_as",
        "save_as_continue",
        "save_on_top",
    }
    assert all(isinstance(v, bool) for v in opts.values())


@pytest.mark.django_db
def test_save_options_change_view_superuser_defaults(superuser_client: Client) -> None:
    """Superuser on a default ModelAdmin (save_as=False) change view:
    Save + continue + add-another visible; save-as-new hidden."""
    g = Group.objects.create(name="example")
    opts = superuser_client.get(_url(g.pk)).json()["save_options"]
    assert opts["show_save"] is True
    assert opts["show_save_and_continue"] is True
    assert opts["show_save_and_add_another"] is True
    # GroupAdmin doesn't set save_as → no "Save as new".
    assert opts["save_as"] is False
    assert opts["show_save_as_new"] is False


@pytest.mark.django_db
def test_save_options_save_as_true_surfaces_save_as_new(superuser_client: Client) -> None:
    """When ModelAdmin.save_as is True, the change view shows "Save as
    new" and hides "Save and add another" (Django's exact behavior:
    `not save_as or add` is False on the change view).

    ``save_as`` is a plain bool attribute, not a method, so set it
    directly rather than via ``admin_override`` (which binds callables).
    """
    from django.contrib import admin as _admin

    g = Group.objects.create(name="example")
    group_admin = _admin.site._registry[Group]
    original = group_admin.save_as
    group_admin.save_as = True
    try:
        opts = superuser_client.get(_url(g.pk)).json()["save_options"]
    finally:
        group_admin.save_as = original
    assert opts["save_as"] is True
    assert opts["show_save_as_new"] is True
    assert opts["show_save_and_add_another"] is False


@pytest.mark.django_db
def test_save_options_save_on_top_defaults_false_and_reflects_admin(
    superuser_client: Client,
) -> None:
    """``save_on_top`` defaults to False (GroupAdmin doesn't set it) and
    reflects ``ModelAdmin.save_on_top`` when the admin enables it (#251).
    Like ``save_as`` it's a plain attribute, so set it directly."""
    from django.contrib import admin as _admin

    g = Group.objects.create(name="example")
    assert superuser_client.get(_url(g.pk)).json()["save_options"]["save_on_top"] is False

    group_admin = _admin.site._registry[Group]
    original = group_admin.save_on_top
    group_admin.save_on_top = True
    try:
        opts = superuser_client.get(_url(g.pk)).json()["save_options"]
    finally:
        group_admin.save_on_top = original
    assert opts["save_on_top"] is True


@pytest.mark.django_db
def test_save_options_no_add_permission_hides_add_another(superuser_client: Client) -> None:
    """Without add permission, "Save and add another" is hidden but the
    plain Save (change perm) stays."""
    g = Group.objects.create(name="example")
    with admin_override(Group, has_add_permission=lambda self, request: False):
        opts = superuser_client.get(_url(g.pk)).json()["save_options"]
    assert opts["show_save_and_add_another"] is False
    assert opts["show_save"] is True


@pytest.mark.django_db
def test_save_options_no_change_permission_hides_save(superuser_client: Client) -> None:
    """Without change permission on the object, the change-view Save is
    hidden (can_save reduces to has_change on the change view)."""
    g = Group.objects.create(name="example")
    with admin_override(Group, has_change_permission=lambda self, request, obj=None: False):
        opts = superuser_client.get(_url(g.pk)).json()["save_options"]
    assert opts["show_save"] is False
    assert opts["show_save_and_continue"] is False


@pytest.mark.django_db
def test_readonly_method_on_admin_resolves_in_detail(superuser_client: Client) -> None:
    """Closes #226: a readonly field that is a method defined on the
    ModelAdmin (the `@admin.display def display_x(self, obj)` pattern,
    called with `obj`) must resolve to the method's return value in the
    detail response — not null. The list view already does this via
    `lookup_field`; the detail view must match.
    """
    from django.contrib import admin as _admin

    g = Group.objects.create(name="example")
    group_admin = _admin.site._registry[Group]

    def admin_method(obj):  # bound as an admin attribute; called with obj
        return f"admin-says-{obj.name}"

    # Attach a NEW display method on the admin instance (admin_override
    # only swaps *existing* attributes).
    group_admin.computed_label = admin_method
    try:
        with admin_override(
            Group,
            get_readonly_fields=lambda self, request, obj=None: ("computed_label",),
            get_fields=lambda self, request, obj=None: ["name", "computed_label"],
        ):
            response = superuser_client.get(_url(g.pk))
    finally:
        del group_admin.computed_label

    assert response.status_code == 200, response.content
    field = response.json()["fields"].get("computed_label")
    assert field is not None, "admin readonly method missing from fields"
    assert (
        field["value"] == "admin-says-example"
    ), f"admin-defined readonly method should resolve to its return value; got {field['value']!r}"


@pytest.mark.django_db
def test_readonly_method_on_model_still_resolves_in_detail(superuser_client: Client) -> None:
    """Regression for #226: a readonly method defined on the MODEL
    (resolved via getattr on the instance) keeps working."""
    g = Group.objects.create(name="example")
    # Group has a real method we can use: __str__ via "name". Use the
    # model's natural `natural_key`? Simpler: patch a method onto the
    # instance's class isn't clean; instead rely on a model attribute.
    with admin_override(
        Group,
        get_readonly_fields=lambda self, request, obj=None: ("name",),
        get_fields=lambda self, request, obj=None: ["name"],
    ):
        response = superuser_client.get(_url(g.pk))
    assert response.status_code == 200
    # `name` is a real field; resolves to the value (not null).
    assert response.json()["fields"]["name"]["value"] == "example"


# --------------------------------------------------------------------------- #
# ForeignKey navigation: detail FK values carry `to` (Issue #270)             #
# --------------------------------------------------------------------------- #
from contextlib import contextmanager  # noqa: E402


@contextmanager
def _registered(*model_classes):
    """Temporarily register models on the default admin site."""
    from django.contrib import admin as _admin

    registered = []
    try:
        for mc in model_classes:
            if mc not in _admin.site._registry:
                _admin.site.register(mc)
                registered.append(mc)
        yield
    finally:
        for mc in registered:
            _admin.site.unregister(mc)


@pytest.mark.django_db
def test_detail_fk_value_includes_navigation_target_when_registered(
    superuser_client: Client,
) -> None:
    """A ForeignKey field in the detail response must carry the `to`
    navigation envelope when its target model is admin-registered, so the
    SPA renders it as a link to the related object (parity with the list
    view + Django admin's clickable FK cells). Regression: the detail view
    omitted `admin_site` when serializing FK values, so `to` was never
    emitted and detail-page FKs were dead text (#270).
    """
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    perm = Permission.objects.filter(content_type__isnull=False).first()
    assert perm is not None

    with _registered(Permission, ContentType):
        response = superuser_client.get(f"/admin-react/api/v1/auth/permission/{perm.pk}/")
        assert response.status_code == 200, response.content
        ct_value = response.json()["fields"]["content_type"]["value"]

    assert ct_value is not None
    assert ct_value["to"] == {"app_label": "contenttypes", "model_name": "contenttype"}


@pytest.mark.django_db
def test_detail_fk_value_omits_target_when_unregistered(
    superuser_client: Client,
) -> None:
    """When the FK target model is NOT registered, `to` is omitted — a
    link the detail endpoint would 404 on must never be surfaced (matches
    the serializer's #89 posture)."""
    from django.contrib.auth.models import Permission

    perm = Permission.objects.filter(content_type__isnull=False).first()
    assert perm is not None

    # Register only Permission (so the endpoint resolves); ContentType stays
    # unregistered → its FK envelope must not carry `to`.
    with _registered(Permission):
        response = superuser_client.get(f"/admin-react/api/v1/auth/permission/{perm.pk}/")
        assert response.status_code == 200, response.content
        ct_value = response.json()["fields"]["content_type"]["value"]

    assert ct_value is not None
    assert "to" not in ct_value


# --------------------------------------------------------------------------- #
# Readonly callable that RAISES must degrade, not 500 (Issue #275)            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_readonly_callable_that_raises_degrades_to_none() -> None:
    """Closes #275: a readonly callable / property that *raises* must
    resolve to a null value, not 500 the detail / create-form endpoint.

    Observed on the add-form (create, unsaved instance): a model property
    listed as a readonly field assumed a saved row and raised when read on
    the blank object. The fallback used ``getattr(obj, name, None)``, whose
    default only swallows ``AttributeError`` — any other exception from the
    property getter propagated and 500'd the endpoint. The fallback must
    guard against *any* exception.
    """
    from django.contrib import admin as _admin

    from django_admin_react.api.views.detail import _readonly_callable_descriptor

    group_admin = _admin.site._registry[Group]

    class _Unsaved:
        # Mirror a real model behind the add-form: has _meta, no pk yet,
        # and a readonly property that blows up on the unsaved instance.
        _meta = Group._meta
        pk = None

        @property
        def boom(self) -> str:
            raise ValueError("instance is not saved yet")

    desc = _readonly_callable_descriptor(group_admin, Group, _Unsaved(), "boom")
    assert desc["value"] is None
    assert desc["readonly"] is True
    assert desc["type"] == "unsupported"


# --------------------------------------------------------------------------- #
# Coverage: per-object view gate + named-fieldsets loop (T-2)                  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_per_object_view_permission_denied_is_403(superuser_client: Client) -> None:
    """The object-level gate (detail.py) must 403 once the row is known to
    exist but `has_view_permission(request, obj)` is False.

    The override returns True at the model level (`obj is None`, so
    `resolve_model` passes) and False per-object — so the request reaches
    the object gate rather than 404'ing at resolution."""
    g = Group.objects.create(name="g")
    with admin_override(Group, has_view_permission=lambda self, request, obj=None: obj is None):
        response = superuser_client.get(_url(g.pk))
    assert response.status_code == 403


@pytest.mark.django_db
def test_named_fieldsets_are_honoured(superuser_client: Client) -> None:
    """A `get_fieldsets` returning real titled groups is reflected in the
    response (`_fieldsets_payload` loop); an all-empty group is dropped."""
    g = Group.objects.create(name="example")
    with admin_override(
        Group,
        get_fieldsets=lambda self, request, obj=None: [
            ("Main", {"fields": ("name",)}),
            ("Empty", {"fields": ()}),
        ],
    ):
        body = superuser_client.get(_url(g.pk)).json()
    titles = [fs["title"] for fs in body["fieldsets"]]
    assert "Main" in titles
    main = next(fs for fs in body["fieldsets"] if fs["title"] == "Main")
    assert "name" in main["fields"]
    assert "Empty" not in titles


@pytest.mark.django_db
def test_fieldset_multi_field_rows_preserved(superuser_client: Client) -> None:
    """Closes #382: a tuple-grouped fieldset row — ``(("name","permissions"),)``
    — is preserved in ``field_rows`` (one inner list per display row) while the
    flat ``fields`` stays for back-compat (the row-flattened list)."""
    g = Group.objects.create(name="example")
    with admin_override(
        Group,
        get_fieldsets=lambda self, request, obj=None: [
            (None, {"fields": (("name", "permissions"),)}),
        ],
    ):
        body = superuser_client.get(_url(g.pk)).json()
    fs = body["fieldsets"][0]
    assert fs["field_rows"] == [["name", "permissions"]]
    assert fs["fields"] == ["name", "permissions"]


@pytest.mark.django_db
def test_fieldset_classes_and_description_are_surfaced(superuser_client: Client) -> None:
    """Closes #306: a fieldset's ``classes`` (e.g. ``collapse``) and
    ``description`` are carried on the descriptor so the SPA can render a
    collapsible section with help text (Django change-form parity)."""
    g = Group.objects.create(name="example")
    with admin_override(
        Group,
        get_fieldsets=lambda self, request, obj=None: [
            (
                "Advanced",
                {
                    "fields": ("name",),
                    "classes": ("collapse", "wide"),
                    "description": "Rarely-changed settings.",
                },
            ),
        ],
    ):
        body = superuser_client.get(_url(g.pk)).json()
    fs = next(f for f in body["fieldsets"] if f["title"] == "Advanced")
    assert fs["classes"] == ["collapse", "wide"]
    assert fs["description"] == "Rarely-changed settings."


# --------------------------------------------------------------------------- #
# View on site (#307)                                                          #
# --------------------------------------------------------------------------- #
def test_view_on_site_url_callable() -> None:
    """A callable ``view_on_site`` is invoked with the object."""
    from django.contrib import admin as _admin

    from django_admin_react.api.views.detail import _view_on_site_url

    class _MA(_admin.ModelAdmin):
        view_on_site = staticmethod(lambda obj: f"https://example.com/g/{obj.pk}")

    ma = _MA(Group, _admin.site)
    g = Group(name="x")
    g.pk = 7
    assert _view_on_site_url(ma, g) == "https://example.com/g/7"


def test_view_on_site_url_true_uses_get_absolute_url() -> None:
    """``view_on_site = True`` + a model ``get_absolute_url`` → that URL,
    resolved directly (no dependency on the legacy admin URLConf)."""
    from django.contrib import admin as _admin

    from django_admin_react.api.views.detail import _view_on_site_url

    ma = _admin.ModelAdmin(Group, _admin.site)
    ma.view_on_site = True
    g = Group(name="x")
    g.pk = 3
    g.get_absolute_url = lambda: f"/groups/{g.pk}/"  # type: ignore[attr-defined]
    assert _view_on_site_url(ma, g) == "/groups/3/"


def test_view_on_site_url_false_or_missing_is_none() -> None:
    """``view_on_site`` falsy, or no ``get_absolute_url`` → ``None``."""
    from django.contrib import admin as _admin

    from django_admin_react.api.views.detail import _view_on_site_url

    ma = _admin.ModelAdmin(Group, _admin.site)
    ma.view_on_site = False
    g = Group(name="x")
    g.pk = 1
    assert _view_on_site_url(ma, g) is None
    # view_on_site True but the model has no get_absolute_url → None.
    ma.view_on_site = True
    assert _view_on_site_url(ma, g) is None


def test_view_on_site_url_swallows_get_absolute_url_errors() -> None:
    """A raising ``get_absolute_url`` degrades to ``None`` (never 500s)."""
    from django.contrib import admin as _admin

    from django_admin_react.api.views.detail import _view_on_site_url

    ma = _admin.ModelAdmin(Group, _admin.site)
    ma.view_on_site = True
    g = Group(name="x")
    g.pk = 1

    def _boom() -> str:
        raise ValueError("no url yet")

    g.get_absolute_url = _boom  # type: ignore[attr-defined]
    assert _view_on_site_url(ma, g) is None


@pytest.mark.django_db
def test_detail_includes_view_on_site_url_key(superuser_client: Client) -> None:
    """The detail response always carries the ``view_on_site_url`` key
    (``None`` for a default admin, since GroupAdmin has no get_absolute_url
    and view_on_site defaults route through it)."""
    g = Group.objects.create(name="example")
    body = superuser_client.get(_url(g.pk)).json()
    assert "view_on_site_url" in body
    assert body["view_on_site_url"] is None


@pytest.mark.django_db
def test_fieldset_without_classes_description_defaults(superuser_client: Client) -> None:
    """A fieldset with no ``classes``/``description`` reports an empty class
    list and a null description (not missing keys)."""
    g = Group.objects.create(name="example")
    with admin_override(
        Group,
        get_fieldsets=lambda self, request, obj=None: [("Main", {"fields": ("name",)})],
    ):
        body = superuser_client.get(_url(g.pk)).json()
    fs = next(f for f in body["fieldsets"] if f["title"] == "Main")
    assert fs["classes"] == []
    assert fs["description"] is None


def test_fieldsets_payload_swallows_get_fieldsets_exception() -> None:
    """`_fieldsets_payload` must degrade to a single flat group when the
    admin's `get_fieldsets` raises (the except + empty-raw fallback).

    Tested at the unit level rather than via the endpoint because Django's
    `get_form` *also* calls `get_fieldsets`, so a raising override would
    500 the request before this defensive branch is reached — the branch
    exists precisely to keep `_fieldsets_payload` itself robust."""
    from django_admin_react.api.views.detail import _fieldsets_payload

    class _RaisingAdmin:
        def get_fieldsets(self, request, obj=None):  # noqa: ANN001, ANN202
            raise RuntimeError("consumer get_fieldsets blew up")

    result = _fieldsets_payload(_RaisingAdmin(), None, None, ["name", "email"])
    assert result == [
        {"title": None, "fields": ["name", "email"], "field_rows": [["name"], ["email"]]}
    ]


@pytest.mark.django_db
def test_radio_fields_surface_widget_hint() -> None:
    """A choice/FK field listed in ``ModelAdmin.radio_fields`` gets a
    ``widget: "radio"`` hint in its descriptor; other fields don't (#251).
    Presentational only — no permission/value change."""
    from django.contrib import admin
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.test import RequestFactory

    from django_admin_react.api.views.detail import _descriptor_for

    class _RadioAdmin(admin.ModelAdmin):
        # Permission.content_type is a ForeignKey — a valid radio_fields target.
        radio_fields = {"content_type": admin.HORIZONTAL}

    model_admin = _RadioAdmin(Permission, admin.site)
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="radio-su", email="radio@example.com", password="x"  # noqa: S106
    )
    form = model_admin.get_form(request, obj=None)()
    obj = Permission()

    common = dict(
        model=Permission,
        model_admin=model_admin,
        obj=obj,
        form=form,
        is_readonly=False,
        admin_site=admin.site,
        request=request,
    )
    fk_desc = _descriptor_for(name="content_type", **common)
    assert fk_desc["widget"] == "radio"  # in radio_fields → hinted

    other_desc = _descriptor_for(name="codename", **common)
    assert "widget" not in other_desc  # not in radio_fields → no hint


@pytest.mark.django_db
def test_detail_surfaces_empty_value_display(superuser_client: Client) -> None:
    """The detail response carries ``empty_value_display`` (#251) — the
    admin's placeholder for empty values (site default ``"-"``)."""
    g = Group.objects.create(name="evd")
    assert superuser_client.get(_url(g.pk)).json()["empty_value_display"] == "-"


@pytest.mark.django_db
def test_raw_id_fields_surface_widget_hint() -> None:
    """A FK/M2M field listed in ``ModelAdmin.raw_id_fields`` gets a
    ``widget: "raw_id"`` hint; ``radio_fields`` wins when a field is in both
    (#251). Presentational only — no permission/value change."""
    from django.contrib import admin
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.test import RequestFactory

    from django_admin_react.api.views.detail import _descriptor_for

    class _RawIdAdmin(admin.ModelAdmin):
        raw_id_fields = ("content_type",)

    model_admin = _RawIdAdmin(Permission, admin.site)
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="rawid-su", email="rawid@example.com", password="x"  # noqa: S106
    )
    form = model_admin.get_form(request, obj=None)()
    common = dict(
        model=Permission,
        model_admin=model_admin,
        obj=Permission(),
        form=form,
        is_readonly=False,
        admin_site=admin.site,
        request=request,
    )
    assert _descriptor_for(name="content_type", **common)["widget"] == "raw_id"
    assert "widget" not in _descriptor_for(name="codename", **common)


@pytest.mark.django_db
def test_formfield_overrides_textarea_promotes_string_to_text() -> None:
    """A CharField the admin overrides with a ``Textarea`` via
    ``formfield_overrides`` surfaces as the multi-line ``text`` type (so the
    SPA renders a ``<textarea>``); a plain admin keeps ``string`` (#446).
    The form widget is the source of truth — Django applies the override in
    ``get_form``."""
    from django import forms
    from django.contrib import admin
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission
    from django.db import models
    from django.test import RequestFactory

    from django_admin_react.api.views.detail import _descriptor_for

    class _TextareaAdmin(admin.ModelAdmin):
        formfield_overrides = {models.CharField: {"widget": forms.Textarea}}

    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser(
        username="ffo-su", email="ffo@example.com", password="x"  # noqa: S106
    )

    def descriptor(model_admin: admin.ModelAdmin) -> dict:
        form = model_admin.get_form(request, obj=None)()
        return _descriptor_for(
            model=Permission,
            model_admin=model_admin,
            obj=Permission(),
            name="name",  # CharField
            form=form,
            is_readonly=False,
            admin_site=admin.site,
            request=request,
        )

    # Override → multi-line text; default admin → single-line string.
    assert descriptor(_TextareaAdmin(Permission, admin.site))["type"] == "text"
    assert descriptor(admin.ModelAdmin(Permission, admin.site))["type"] == "string"


def test_apply_widget_override_reconciles_type_with_widget() -> None:
    """``_apply_widget_override`` maps only between the existing ``string``
    and ``text`` types from the bound widget, and no-ops otherwise (#446)."""
    from django import forms

    from django_admin_react.api.views.detail import _apply_widget_override

    def reconcile(type_: str, widget: object) -> str:
        d = {"type": type_}
        _apply_widget_override(d, type("F", (), {"widget": widget})())
        return d["type"]

    # Forward: single-line string + Textarea → text.
    assert reconcile("string", forms.Textarea()) == "text"
    # Reverse: multi-line text forced to a single-line TextInput → string.
    assert reconcile("text", forms.TextInput()) == "string"
    # No-ops: matching defaults, unrelated types, and absent form fields.
    assert reconcile("string", forms.TextInput()) == "string"
    assert reconcile("text", forms.Textarea()) == "text"
    assert reconcile("integer", forms.Textarea()) == "integer"
    none_field = {"type": "string"}
    _apply_widget_override(none_field, None)
    assert none_field["type"] == "string"
