"""Tests for ``GET /api/v1/<app>/<model>/`` (PR #4).

Mandatory 8-row matrix per CLAUDE.md §6 + ACCEPTANCE.md §3.5 T-1.
Plus feature-specific tests: search delegation, ordering validation,
columns from get_list_display, permissions booleans, sensitive-field
not leaked.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextlib import suppress

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import Client

from tests.helpers import admin_override


@contextmanager
def _admin_attrs(model_cls: type, **values: object):
    """Temporarily set plain (non-method) attributes on a registered
    ``ModelAdmin`` — e.g. ``show_full_result_count``. (``admin_override``
    only binds callables.)"""
    model_admin = admin.site._registry[model_cls]
    sentinel = object()
    originals: dict[str, object] = {}
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


# Use auth.Group as the test target — it's always registered in admin,
# has a name field for list_display tests, and has search_fields.

LIST_URL = "/admin-react/api/v1/auth/group/"


# --------------------------------------------------------------------------- #
# Mandatory 8-row matrix                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_unauthorized(anon_client: Client) -> None:
    response = anon_client.get(LIST_URL)
    assert response.status_code in (302, 403)
    body = response.content.decode("utf-8", errors="replace")
    assert "password" not in body.lower()


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    response = user_client.get(LIST_URL)
    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "forbidden", "message": "You do not have permission."}
    }


@pytest.mark.django_db
def test_superuser_with_permission_succeeds(superuser_client: Client) -> None:
    Group.objects.create(name="example")
    response = superuser_client.get(LIST_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["app_label"] == "auth"
    assert body["model_name"] == "group"
    assert isinstance(body["columns"], list)
    assert "permissions" in body
    assert "results" in body


@pytest.mark.django_db
def test_list_response_reports_pk_field(superuser_client: Client) -> None:
    """The list response names the model's primary-key field so the SPA
    can pin / never-truncate / lock that column (#360)."""
    response = superuser_client.get(LIST_URL)
    assert response.status_code == 200
    assert response.json()["pk_field"] == "id"


# --------------------------------------------------------------------------- #
# show_full_result_count parity (#311): full_count reports the unfiltered     #
# base total when the list is narrowed                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_full_count_equals_total_when_not_narrowed(superuser_client: Client) -> None:
    """An unnarrowed list reports ``full_count == total`` (no second count)."""
    Group.objects.create(name="alpha")
    Group.objects.create(name="beta")
    body = superuser_client.get(LIST_URL).json()
    assert body["total"] == 2
    assert body["full_count"] == 2


@pytest.mark.django_db
def test_full_count_reports_unfiltered_total_when_searched(superuser_client: Client) -> None:
    """A search-narrowed list keeps ``full_count`` at the unfiltered base
    count (GroupAdmin searches ``name``) so the SPA can show "X of Y" (#311)."""
    Group.objects.create(name="alpha")
    Group.objects.create(name="apex")
    Group.objects.create(name="beta")
    body = superuser_client.get(LIST_URL, {"q": "alpha"}).json()
    assert body["total"] == 1  # only "alpha" matches
    assert body["full_count"] == 3  # unfiltered base


@pytest.mark.django_db
def test_full_count_null_when_show_full_result_count_disabled(superuser_client: Client) -> None:
    """``show_full_result_count = False`` opts out of the extra COUNT(*):
    ``full_count`` is ``null`` even when the list is narrowed (#311)."""
    Group.objects.create(name="alpha")
    Group.objects.create(name="beta")
    with _admin_attrs(Group, show_full_result_count=False):
        body = superuser_client.get(LIST_URL, {"q": "alpha"}).json()
    assert body["total"] == 1
    assert body["full_count"] is None


# --------------------------------------------------------------------------- #
# "Show all N" parity (#385): list_max_show_all + the ``all`` (ALL_VAR) flag  #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_list_response_exposes_list_max_show_all(superuser_client: Client) -> None:
    """The list payload carries ``list_max_show_all`` (Django default 200)
    so the SPA knows when to offer the "Show all N" control (#385)."""
    body = superuser_client.get(LIST_URL).json()
    assert body["list_max_show_all"] == 200


@pytest.mark.django_db
def test_all_param_returns_every_row_when_under_limit(superuser_client: Client) -> None:
    """``?all`` drops pagination and returns all rows on one page when the
    count is at/below ``list_max_show_all`` (#385)."""
    for i in range(5):
        Group.objects.create(name=f"g{i}")
    body = superuser_client.get(LIST_URL, {"page_size": "2", "all": ""}).json()
    assert body["page"] == 1
    assert body["total"] == 5
    # Pagination is dropped: every row comes back despite page_size=2.
    assert len(body["results"]) == 5
    assert body["page_size"] == 5


@pytest.mark.django_db
def test_all_param_ignored_when_over_limit(superuser_client: Client) -> None:
    """When ``total`` exceeds ``list_max_show_all``, ``?all`` is ignored and
    the list paginates normally — Django's guard against an unbounded
    materialise (#385). Shrink the cap via the admin attr to keep the test
    cheap."""
    for i in range(5):
        Group.objects.create(name=f"g{i}")
    with _admin_attrs(Group, list_max_show_all=3):
        body = superuser_client.get(LIST_URL, {"page_size": "2", "all": ""}).json()
    assert body["total"] == 5
    assert body["list_max_show_all"] == 3
    # Over the cap → ?all ignored → normal page slice of page_size=2.
    assert body["page_size"] == 2
    assert len(body["results"]) == 2


@pytest.mark.django_db
def test_all_param_does_not_narrow_full_count(superuser_client: Client) -> None:
    """``all`` is a page-management flag, not a filter: it must not flip the
    list into the narrowed ``full_count`` branch (#385/#311)."""
    Group.objects.create(name="alpha")
    Group.objects.create(name="beta")
    body = superuser_client.get(LIST_URL, {"all": ""}).json()
    assert body["total"] == 2
    assert body["full_count"] == 2


@pytest.mark.django_db
def test_user_without_view_permission_forbidden(superuser_client: Client) -> None:
    with admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
        response = superuser_client.get(LIST_URL)
    # resolve_model returns None when has_view_permission is False, so a 404
    # is acceptable per the deny-by-default rule (S-11/S-12).
    assert response.status_code in (403, 404)


@pytest.mark.django_db
def test_unregistered_model_not_found(superuser_client: Client) -> None:
    response = superuser_client.get("/admin-react/api/v1/auth/nope/")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not found."}}


@pytest.mark.django_db
def test_csrf_irrelevant_on_get(superuser_client: Client) -> None:
    """GET is a safe method; CSRF protection does not apply."""
    response = superuser_client.get(LIST_URL)
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Feature-specific                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_list_surfaces_search_help_text(superuser_client: Client) -> None:
    """ModelAdmin.search_help_text is surfaced for the SPA to show under the
    search box (#445); empty string when unset."""
    assert superuser_client.get(LIST_URL).json()["search_help_text"] == ""
    with _admin_attrs(Group, search_help_text="Search by group name."):
        body = superuser_client.get(LIST_URL).json()
    assert body["search_help_text"] == "Search by group name."


@pytest.mark.django_db
def test_search_delegates_to_admin_get_search_results(superuser_client: Client) -> None:
    Group.objects.create(name="alpha")
    Group.objects.create(name="beta")
    response = superuser_client.get(LIST_URL + "?q=alpha")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["label"] == "alpha"


@pytest.mark.django_db
def test_pagination_clamps_page_size(superuser_client: Client) -> None:
    for i in range(5):
        Group.objects.create(name=f"g{i}")
    response = superuser_client.get(LIST_URL + "?page=1&page_size=2")
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["results"]) == 2
    assert body["total"] >= 5


@pytest.mark.django_db
def test_ordering_with_unknown_token_is_silently_dropped(superuser_client: Client) -> None:
    Group.objects.create(name="zebra")
    Group.objects.create(name="aardvark")
    response = superuser_client.get(LIST_URL + "?ordering=nonexistent_field")
    # Must not 500; the unknown token is dropped per contract §7.
    assert response.status_code == 200


@pytest.mark.django_db
def test_permissions_match_admin_answers(superuser_client: Client) -> None:
    response = superuser_client.get(LIST_URL)
    body = response.json()
    perms = body["permissions"]
    assert set(perms.keys()) == {"view", "add", "change", "delete"}
    assert all(isinstance(v, bool) for v in perms.values())


@pytest.mark.django_db
def test_starts_from_admin_get_queryset(superuser_client: Client) -> None:
    """The list endpoint must not call Model.objects.all() directly.

    We assert this by overriding get_queryset to return an empty queryset
    and confirming the response contains no rows even though objects exist.
    """
    Group.objects.create(name="hidden")
    with admin_override(
        Group,
        get_queryset=lambda self, request: Group.objects.none(),
    ):
        response = superuser_client.get(LIST_URL)
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["total"] == 0


@pytest.mark.django_db
def test_list_response_exposes_object_name_and_verbose_name(superuser_client: Client) -> None:
    """The list response carries enough metadata for the SPA to render
    the model name *as written* — not the lowercased ``model_name``.

    Without ``object_name`` / ``verbose_name`` / ``verbose_name_plural``
    on the wire, the SPA can only fall back to ``model_name`` (lowercase,
    no separators), which produces titles like
    ``Packagemodeldisclaimerdisplayed`` for a class literally named
    ``PackageModelDisclaimerDisplayed``.
    """
    response = superuser_client.get(LIST_URL)
    assert response.status_code == 200
    body = response.json()
    # auth.Group has no Meta.verbose_name override, so Django auto-derives.
    assert body["object_name"] == "Group"  # class name as written
    assert body["verbose_name"] == "group"
    assert body["verbose_name_plural"] == "groups"
    # ``model_name`` stays lowercase (used in URLs) — regression guard.
    assert body["model_name"] == "group"


@pytest.mark.django_db
def test_columns_payload_passes_request_to_get_sortable_by(
    superuser_client: Client,
) -> None:
    """Regression: ``_columns_payload`` must call ``get_sortable_by(request)``
    with a real request, not ``None``.

    Third-party admin wrappers (e.g. ``django-admin-flexlist``) replace
    ``ModelAdmin.get_list_display`` with a function that reads
    ``request.user``. ``get_sortable_by`` falls back to
    ``get_list_display`` when the admin has no explicit ``sortable_by``,
    so a stale ``None`` here crashes the wrapped function and the whole
    list endpoint 500s — which in the SPA presents as ``"No objects yet."``
    even when the DB has rows.

    This test asserts the request flows through. The cheapest signal is
    that ``get_sortable_by`` was called *at all* with the request that
    the SPA passed in.
    """
    seen: dict[str, object] = {}

    def _gsb(self, request) -> tuple[str, ...]:
        seen["request"] = request
        return ("name",)

    with admin_override(Group, get_sortable_by=_gsb):
        response = superuser_client.get(LIST_URL)

    assert response.status_code == 200
    assert "request" in seen, "_columns_payload did not call get_sortable_by"
    assert seen["request"] is not None, (
        "_columns_payload called get_sortable_by(None) — third-party wrappers "
        "(django-admin-flexlist, etc.) that read request.user will crash, "
        "and the whole list endpoint will 500."
    )
    # And the `sortable` flag should reflect the override.
    columns = response.json()["columns"]
    by_name = {c["name"]: c for c in columns}
    if "name" in by_name:
        assert by_name["name"]["sortable"] is True


# --------------------------------------------------------------------------- #
# Pagination / ordering / search query-param handling (T-2 coverage)          #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_garbage_page_param_defaults_to_one(superuser_client: Client) -> None:
    """``?page=abc`` must not 500 — falls back to page 1 (list.py _clamp_page)."""
    Group.objects.create(name="g")
    response = superuser_client.get(LIST_URL + "?page=abc")
    assert response.status_code == 200
    assert response.json()["page"] == 1


@pytest.mark.django_db
def test_garbage_page_size_defaults(superuser_client: Client) -> None:
    """``?page_size=abc`` falls back to the default (list.py _clamp_page_size)."""
    Group.objects.create(name="g")
    response = superuser_client.get(LIST_URL + "?page_size=abc")
    assert response.status_code == 200
    assert response.json()["page_size"] >= 1


@pytest.mark.django_db
def test_page_size_below_one_defaults(superuser_client: Client) -> None:
    """``?page_size=0`` falls back to the default rather than an empty window."""
    Group.objects.create(name="g")
    response = superuser_client.get(LIST_URL + "?page_size=0")
    assert response.status_code == 200
    assert response.json()["page_size"] >= 1


@pytest.mark.django_db
def test_ordering_valid_token_applied(superuser_client: Client) -> None:
    """A ``?ordering=`` token in the admin's sortable set is honoured
    (list.py _apply_ordering valid-token path)."""
    Group.objects.create(name="b")
    Group.objects.create(name="a")
    # Pin "name" as sortable so the token is definitely allowed.
    with admin_override(Group, get_sortable_by=lambda self, request: ("name",)):
        response = superuser_client.get(LIST_URL + "?ordering=name")
    assert response.status_code == 200
    assert response.json()["results"]


@pytest.mark.django_db
def test_ordering_unknown_token_is_dropped(superuser_client: Client) -> None:
    """An ``?ordering=`` token NOT in the admin's allowed set is silently
    dropped (no crash, no injection) — list.py _apply_ordering."""
    Group.objects.create(name="g")
    response = superuser_client.get(LIST_URL + "?ordering=not_a_real_field")
    assert response.status_code == 200


@pytest.mark.django_db
def test_search_distinct_when_may_have_duplicates(superuser_client: Client) -> None:
    """When the admin's search signals possible duplicates, the list
    de-duplicates with ``.distinct()`` (list.py search branch)."""
    Group.objects.create(name="alpha")
    with admin_override(
        Group,
        get_search_results=lambda self, request, queryset, term: (queryset, True),
    ):
        response = superuser_client.get(LIST_URL + "?q=al")
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Choice fields show the display label, not the raw stored value (#298)       #
# --------------------------------------------------------------------------- #
def test_list_cell_choice_field_shows_display_label(monkeypatch) -> None:  # noqa: ANN001
    """A list cell for a field with ``choices`` renders the human label
    (Django's ``display_for_field`` parity), e.g. ``"h"`` → "High". Unknown
    values fall through to the normal serializer."""
    from django.db import models

    from django_admin_react.api.views import list as list_view

    field = models.CharField(choices=[("h", "High"), ("l", "Low")])
    monkeypatch.setattr(list_view, "safe_get_field", lambda obj, name: field)

    assert list_view._serialize_list_value(object(), "priority", "h") == "High"
    assert list_view._serialize_list_value(object(), "priority", "l") == "Low"
    # A value not in the choice set is left to the default serializer.
    assert list_view._serialize_list_value(object(), "priority", "x") == "x"


def test_list_cell_non_choice_field_unaffected(monkeypatch) -> None:  # noqa: ANN001
    """A plain field without choices still serializes its value as-is."""
    from django.db import models

    from django_admin_react.api.views import list as list_view

    field = models.CharField()
    monkeypatch.setattr(list_view, "safe_get_field", lambda obj, name: field)

    assert list_view._serialize_list_value(object(), "name", "hello") == "hello"


# --------------------------------------------------------------------------- #
# list_select_related — avoid N+1 on FK columns (#305)                        #
# --------------------------------------------------------------------------- #
def test_has_related_field_in_list_display_detects_fk() -> None:
    """A forward FK in list_display is detected; non-relation columns and
    unknown / method names are not."""
    from django.contrib import admin
    from django.contrib.auth.models import Permission

    from django_admin_react.api.views import list as list_view

    ma = admin.ModelAdmin(Permission, admin.site)
    # Permission.content_type is a ForeignKey.
    assert list_view._has_related_field_in_list_display(ma, ["content_type"]) is True
    assert list_view._has_related_field_in_list_display(ma, ["codename", "name"]) is False
    assert list_view._has_related_field_in_list_display(ma, ["not_a_field"]) is False


def test_apply_select_related_auto_when_fk_in_list_display() -> None:
    """Default (list_select_related=False): auto select_related() when a FK
    column is present, and a no-op otherwise."""
    from django.contrib import admin
    from django.contrib.auth.models import Permission

    from django_admin_react.api.views import list as list_view

    ma = admin.ModelAdmin(Permission, admin.site)
    qs = Permission.objects.all()
    assert list_view._apply_select_related(qs, ma, ["content_type"]).query.select_related
    assert not list_view._apply_select_related(qs, ma, ["codename"]).query.select_related


def test_apply_select_related_honours_explicit_list() -> None:
    """A list/tuple list_select_related is applied verbatim."""
    from django.contrib import admin
    from django.contrib.auth.models import Permission

    from django_admin_react.api.views import list as list_view

    class _MA(admin.ModelAdmin):
        list_select_related = ["content_type"]

    ma = _MA(Permission, admin.site)
    qs = Permission.objects.all()
    out = list_view._apply_select_related(qs, ma, ["codename"])
    assert out.query.select_related == {"content_type": {}}


def test_apply_select_related_true_follows_all_fks() -> None:
    """list_select_related = True → select_related() (all FKs)."""
    from django.contrib import admin
    from django.contrib.auth.models import Permission

    from django_admin_react.api.views import list as list_view

    class _MA(admin.ModelAdmin):
        list_select_related = True

    ma = _MA(Permission, admin.site)
    out = list_view._apply_select_related(Permission.objects.all(), ma, ["codename"])
    assert out.query.select_related is True


@pytest.mark.django_db
def test_list_surfaces_empty_value_display(superuser_client: Client) -> None:
    """The list response carries ``empty_value_display`` (#251) — the site
    default ``"-"`` or the ``ModelAdmin`` override — so the SPA renders it
    for empty cells instead of a hardcoded em-dash."""
    assert superuser_client.get(LIST_URL).json()["empty_value_display"] == "-"
    model_admin = admin.site._registry[Group]
    model_admin.empty_value_display = "(none)"
    try:
        body = superuser_client.get(LIST_URL).json()
    finally:
        del model_admin.empty_value_display  # restore the class/site default
    assert body["empty_value_display"] == "(none)"
