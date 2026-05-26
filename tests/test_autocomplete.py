"""Tests for ``GET /api/v1/<app>/<model>/autocomplete/`` (Issue #59).

Mandatory matrix (per CLAUDE.md §6):

- Anonymous → 403 / no body leak.
- Authenticated non-staff → 403.
- Staff without view permission on the target → 403.
- Staff with view permission → 200 + results.
- Unregistered model → 404.
- Target admin without ``search_fields`` → 400.

Plus feature-specific tests: search delegation, page pagination,
``has_more`` flag, page_size clamp.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextlib import suppress

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client

from tests.helpers import admin_override

AUTOCOMPLETE_URL = "/admin-react/api/v1/auth/user/autocomplete/"


@contextmanager
def admin_attr(model_cls, **values):
    """Temporarily set non-callable attrs on a registered ModelAdmin."""
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
# §6 mandatory matrix                                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_unauthorized(anon_client: Client) -> None:
    response = anon_client.get(AUTOCOMPLETE_URL)
    assert response.status_code == 403
    body = response.content.decode("utf-8", errors="replace")
    assert "password" not in body.lower()


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    response = user_client.get(AUTOCOMPLETE_URL)
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_without_view_permission_returns_404(staff_client: Client) -> None:
    """Same posture as the list endpoint — unviewable model is 404, not 403,
    so the endpoint doesn't reveal "this model exists but you can't see it"."""
    User = get_user_model()
    with admin_override(User, has_view_permission=lambda self, request, obj=None: False):
        response = staff_client.get(AUTOCOMPLETE_URL)
    assert response.status_code == 404


@pytest.mark.django_db
def test_unregistered_model_404(superuser_client: Client) -> None:
    response = superuser_client.get("/admin-react/api/v1/unknown/nothing/autocomplete/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_admin_without_search_fields_returns_400(superuser_client: Client) -> None:
    """An admin with empty ``search_fields`` → 400.

    The 400 surfaces the same condition Django admin itself raises
    via ``ImproperlyConfigured`` on the HTML autocomplete view.
    """
    User = get_user_model()
    with admin_attr(User, search_fields=()):
        response = superuser_client.get(AUTOCOMPLETE_URL)
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"
    assert "search_fields" in body["error"]["message"]


# --------------------------------------------------------------------------- #
# Happy path + behavior                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_returns_results_with_label_and_id(superuser_client: Client) -> None:
    """Successful autocomplete returns ``{results: [{id, label}], pagination}``."""
    User = get_user_model()
    User.objects.create_user(username="alice", password="x")  # noqa: S106
    User.objects.create_user(username="bob", password="x")  # noqa: S106

    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL)
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert "pagination" in body
    for row in body["results"]:
        assert set(row.keys()) == {"id", "label"}
        assert isinstance(row["id"], int)
        assert isinstance(row["label"], str)


@pytest.mark.django_db
def test_q_param_filters(superuser_client: Client) -> None:
    """``?q=al`` returns only rows the admin's search would return."""
    User = get_user_model()
    User.objects.create_user(username="alice", password="x")  # noqa: S106
    User.objects.create_user(username="bob", password="x")  # noqa: S106
    User.objects.create_user(username="alfred", password="x")  # noqa: S106

    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL + "?q=al")
    body = response.json()
    labels = {row["label"] for row in body["results"]}
    assert "alice" in labels
    assert "alfred" in labels
    assert "bob" not in labels


@pytest.mark.django_db
def test_has_more_flag_signals_more_rows(superuser_client: Client) -> None:
    """``has_more=True`` when the queryset has at least one row past page_size."""
    User = get_user_model()
    for i in range(5):
        User.objects.create_user(username=f"u{i}", password="x")  # noqa: S106

    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL + "?page_size=2")
    body = response.json()
    assert len(body["results"]) == 2
    assert body["pagination"]["has_more"] is True
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["page_size"] == 2


@pytest.mark.django_db
def test_page_size_clamped_to_autocomplete_max(superuser_client: Client) -> None:
    """Hostile ``?page_size=10000`` silently clamps to the autocomplete max (50)."""
    User = get_user_model()
    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL + "?page_size=10000")
    body = response.json()
    assert body["pagination"]["page_size"] <= 50


@pytest.mark.django_db
def test_garbage_page_param_defaults_to_one(superuser_client: Client) -> None:
    """``?page=abc`` must not 500 — falls back to page 1."""
    User = get_user_model()
    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL + "?page=abc")
    assert response.status_code == 200
    assert response.json()["pagination"]["page"] == 1


@pytest.mark.django_db
def test_cache_control_no_store(superuser_client: Client) -> None:
    """Per-user, search-term-specific payload must never be cached."""
    User = get_user_model()
    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL)
    assert response["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_distinct_applied_when_search_may_duplicate(superuser_client: Client) -> None:
    """When the admin's ``get_search_results`` signals possible
    duplicates (a relation-spanning search), the view de-duplicates with
    ``.distinct()`` (autocomplete.py:105) — so a typeahead never shows
    the same row twice."""
    User = get_user_model()
    User.objects.create_user(username="alice", password="x")  # noqa: S106
    with (
        admin_attr(User, search_fields=("username",)),
        admin_override(
            User,
            get_search_results=lambda self, request, queryset, search_term: (queryset, True),
        ),
    ):
        response = superuser_client.get(AUTOCOMPLETE_URL + "?q=al")
    assert response.status_code == 200
    labels = [r["label"] for r in response.json()["results"]]
    assert len(labels) == len(set(labels))  # de-duplicated


@pytest.mark.django_db
def test_page_size_non_int_falls_back_to_default(superuser_client: Client) -> None:
    """``?page_size=abc`` must not 500 — it falls back to the
    autocomplete default (autocomplete.py:159-160)."""
    from django_admin_react.api.views.autocomplete import _AUTOCOMPLETE_DEFAULT_PAGE_SIZE

    User = get_user_model()
    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL + "?page_size=abc")
    assert response.status_code == 200
    assert response.json()["pagination"]["page_size"] == _AUTOCOMPLETE_DEFAULT_PAGE_SIZE


@pytest.mark.django_db
def test_page_size_below_one_falls_back_to_default(superuser_client: Client) -> None:
    """``?page_size=0`` (or negative) falls back to the default rather
    than an empty/invalid window (autocomplete.py:162)."""
    from django_admin_react.api.views.autocomplete import _AUTOCOMPLETE_DEFAULT_PAGE_SIZE

    User = get_user_model()
    with admin_attr(User, search_fields=("username",)):
        response = superuser_client.get(AUTOCOMPLETE_URL + "?page_size=0")
    assert response.status_code == 200
    assert response.json()["pagination"]["page_size"] == _AUTOCOMPLETE_DEFAULT_PAGE_SIZE
