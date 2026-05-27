"""Tests for ``GET /api/v1/<app>/<model>/add/`` — the create-form schema.

Mirrors the mandatory matrix: anon → redirect/403, non-staff → 403,
staff with add perm → 200 + field descriptors, staff without add perm
→ 403, unregistered model → 404.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from django_admin_react.api.views.create_form import _overlay_initial
from django_admin_react.api.views.create_form import _prepopulated_payload
from tests.helpers import admin_override

ADD_URL = "/admin-react/api/v1/auth/group/add/"


@pytest.mark.django_db
def test_anonymous_redirected_or_forbidden(anon_client: Client) -> None:
    r = anon_client.get(ADD_URL)
    assert r.status_code in (302, 403)


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    assert user_client.get(ADD_URL).status_code == 403


@pytest.mark.django_db
def test_staff_with_add_permission_gets_schema(superuser_client: Client) -> None:
    r = superuser_client.get(ADD_URL)
    assert r.status_code == 200
    body = r.json()
    assert body["app_label"] == "auth"
    assert body["model_name"] == "group"
    assert "fieldsets" in body
    assert "fields" in body
    # No pk / label / inlines on the add form (it's for a new object).
    assert "pk" not in body
    assert "inlines" not in body
    # auth.Group has a `name` field — it should be present + writable.
    assert "name" in body["fields"]
    assert body["fields"]["name"]["readonly"] is False


@pytest.mark.django_db
def test_staff_without_add_permission_forbidden(superuser_client: Client) -> None:
    """Create is gated on has_add_permission — not view."""
    with admin_override(Group, has_add_permission=lambda self, request: False):
        r = superuser_client.get(ADD_URL)
    assert r.status_code == 403


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    assert superuser_client.get("/admin-react/api/v1/auth/nonexistent/add/").status_code == 404


@pytest.mark.django_db
def test_add_form_always_carries_prepopulated_fields_key(superuser_client: Client) -> None:
    """The key is always present (empty `{}` when the admin declares none),
    so the SPA can branch without a guard (#245)."""
    body = superuser_client.get(ADD_URL).json()
    assert body["prepopulated_fields"] == {}  # GroupAdmin declares none


# --------------------------------------------------------------------------- #
# _prepopulated_payload filtering (#245): restrict to rendered, non-readonly  #
# targets and rendered sources                                                #
# --------------------------------------------------------------------------- #
def _admin_stub(mapping: dict[str, tuple[str, ...]]) -> SimpleNamespace:
    return SimpleNamespace(get_prepopulated_fields=lambda request, obj: mapping)


def test_prepopulated_keeps_rendered_target_and_sources() -> None:
    out = _prepopulated_payload(
        _admin_stub({"slug": ("title", "subtitle")}), None, ["slug", "title", "subtitle"], set()
    )
    assert out == {"slug": ["title", "subtitle"]}


def test_prepopulated_drops_readonly_target() -> None:
    out = _prepopulated_payload(
        _admin_stub({"slug": ("title",)}), None, ["slug", "title"], {"slug"}
    )
    assert out == {}


def test_prepopulated_filters_unrendered_sources() -> None:
    out = _prepopulated_payload(
        _admin_stub({"slug": ("title", "hidden")}), None, ["slug", "title"], set()
    )
    assert out == {"slug": ["title"]}


def test_prepopulated_drops_target_with_no_usable_sources() -> None:
    out = _prepopulated_payload(_admin_stub({"slug": ("hidden",)}), None, ["slug"], set())
    assert out == {}


def test_prepopulated_empty_when_admin_declares_none() -> None:
    out = _prepopulated_payload(_admin_stub({}), None, ["name"], set())
    assert out == {}


@pytest.mark.django_db
def test_add_form_uses_change_false_form(superuser_client: Client) -> None:
    """The add form must be built with change=False / obj=None — Django's
    add view contract. A consumer get_form that returns a change-only
    form when change=True must not be used for the add path."""
    seen: dict[str, object] = {}
    from django import forms

    add_form = forms.modelform_factory(Group, fields=["name"])

    def branching_get_form(self, request, obj=None, change=False, **kwargs):  # noqa: ANN001
        seen["change"] = change
        seen["obj_is_none"] = obj is None
        return add_form

    with admin_override(Group, get_form=branching_get_form):
        r = superuser_client.get(ADD_URL)

    assert r.status_code == 200
    assert seen.get("change") is False
    assert seen.get("obj_is_none") is True


@pytest.mark.django_db
def test_add_form_includes_save_options_block(superuser_client: Client) -> None:
    """The create-form response carries the add-view save-flow flags (#154)
    so the SPA can render Save / Save-and-add-another / Save-and-continue.
    Computed with obj=None (add semantics): no "Save as new" on the add
    view, and Save / Save-and-add-another available to a user who can add.
    """
    body = superuser_client.get(ADD_URL).json()
    assert "save_options" in body
    so = body["save_options"]
    assert so["show_save"] is True
    assert so["show_save_and_add_another"] is True
    # "Save as new" is a change-view-only affordance — never on add.
    assert so["show_save_as_new"] is False


# --------------------------------------------------------------------------- #
# get_changeform_initial_data / GET-param prefill (#444)                       #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_get_param_prefills_scalar_field(superuser_client: Client) -> None:
    """A link like ``/add/?name=Editors`` lands the add form pre-filled —
    the default ``get_changeform_initial_data`` reflects ``request.GET``."""
    body = superuser_client.get(f"{ADD_URL}?name=Editors").json()
    assert body["fields"]["name"]["value"] == "Editors"


@pytest.mark.django_db
def test_changeform_initial_data_override_prefills(superuser_client: Client) -> None:
    """A ModelAdmin that overrides get_changeform_initial_data seeds the
    add form with its defaults."""
    with admin_override(
        Group, get_changeform_initial_data=lambda self, request: {"name": "Default Team"}
    ):
        body = superuser_client.get(ADD_URL).json()
    assert body["fields"]["name"]["value"] == "Default Team"


@pytest.mark.django_db
def test_no_initial_leaves_default_value(superuser_client: Client) -> None:
    """Without prefill, the field keeps its empty add-form default — the
    overlay only touches fields named in the initial data."""
    body = superuser_client.get(ADD_URL).json()
    assert body["fields"]["name"]["value"] == ""


@pytest.mark.django_db
def test_m2m_initial_not_prefilled(superuser_client: Client) -> None:
    """An M2M can't be set on the unsaved add instance, so an M2M initial
    is ignored — the field keeps its empty default."""
    body = superuser_client.get(f"{ADD_URL}?permissions=1").json()
    assert body["fields"]["permissions"]["value"] == []


@pytest.mark.django_db
def test_unknown_initial_param_is_ignored(superuser_client: Client) -> None:
    """An initial naming a field the form doesn't render is a no-op — no
    crash and no stray key in the payload."""
    r = superuser_client.get(f"{ADD_URL}?not_a_real_field=x")
    assert r.status_code == 200
    assert "not_a_real_field" not in r.json()["fields"]


# --------------------------------------------------------------------------- #
# _overlay_initial unit coverage (#444): FK resolution + skip/ignore branches #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_overlay_resolves_fk_initial_to_envelope() -> None:
    """An FK initial is resolved through the form's (admin-scoped)
    ModelChoiceField queryset and serialized as the {id, label} envelope."""
    from django import forms
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(Group)
    form = forms.modelform_factory(Permission, fields=["name", "content_type", "codename"])()
    fields = {"content_type": {"value": None}}

    _overlay_initial(fields, Permission, form, {"content_type": str(ct.pk)}, None, None)

    assert fields["content_type"]["value"]["id"] == ct.pk


@pytest.mark.django_db
def test_overlay_ignores_invalid_fk_pk() -> None:
    """An FK initial pointing at a non-existent row is ignored (no 500),
    leaving the field's default value."""
    from django import forms
    from django.contrib.auth.models import Permission

    form = forms.modelform_factory(Permission, fields=["content_type"])()
    fields = {"content_type": {"value": None}}

    _overlay_initial(fields, Permission, form, {"content_type": "99999999"}, None, None)

    assert fields["content_type"]["value"] is None


@pytest.mark.django_db
def test_overlay_skips_m2m_initial() -> None:
    """An M2M initial is skipped — not settable on the unsaved add instance."""
    from django import forms

    form = forms.modelform_factory(Group, fields=["name", "permissions"])()
    fields = {"permissions": {"value": []}}

    _overlay_initial(fields, Group, form, {"permissions": ["1"]}, None, None)

    assert fields["permissions"]["value"] == []


def test_overlay_skips_field_absent_from_form() -> None:
    """An initial for a field the form doesn't render leaves the descriptor
    untouched (and never touches the DB)."""
    form = SimpleNamespace(fields={})
    fields = {"name": {"value": "orig"}}

    _overlay_initial(fields, Group, form, {"name": "changed"}, None, None)

    assert fields["name"]["value"] == "orig"
