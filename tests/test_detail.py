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
