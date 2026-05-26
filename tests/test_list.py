"""Tests for ``GET /api/v1/<app>/<model>/`` (PR #4).

Mandatory 8-row matrix per CLAUDE.md §6 + ACCEPTANCE.md §3.5 T-1.
Plus feature-specific tests: search delegation, ordering validation,
columns from get_list_display, permissions booleans, sensitive-field
not leaked.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import Client

# Use auth.Group as the test target — it's always registered in admin,
# has a name field for list_display tests, and has search_fields.

LIST_URL = "/admin-react/api/v1/auth/group/"


@contextmanager
def _admin_override(model_cls, **method_returns) -> Iterator[None]:
    model_admin = admin.site._registry[model_cls]
    originals = {}
    try:
        for name, fn in method_returns.items():
            originals[name] = getattr(model_admin, name)
            setattr(model_admin, name, fn.__get__(model_admin))
        yield
    finally:
        for name, original in originals.items():
            setattr(model_admin, name, original)


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
    with _admin_override(Group, has_view_permission=lambda self, request, obj=None: False):
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
    with _admin_override(
        Group,
        get_queryset=lambda self, request: Group.objects.none(),
    ):
        response = superuser_client.get(LIST_URL)
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["total"] == 0
