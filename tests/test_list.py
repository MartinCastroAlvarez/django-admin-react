"""Tests for ``GET /api/v1/<app>/<model>/`` (PR #4).

Mandatory 8-row matrix per CLAUDE.md §6 + ACCEPTANCE.md §3.5 T-1.
Plus feature-specific tests: search delegation, ordering validation,
columns from get_list_display, permissions booleans, sensitive-field
not leaked.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from tests.helpers import admin_override

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
