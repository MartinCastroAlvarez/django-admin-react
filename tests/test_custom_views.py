"""Tests for custom admin views surfaced to the SPA (Issue #439).

The package introspects ``ModelAdmin.get_urls()`` and exposes the
consumer's *extra* admin routes (everything that isn't the standard
``changelist|add|change|delete|history`` CRUD set) so the SPA can link
out to the Django-rendered page. Each surfaced route carries
``{name, label, url, level}``.

This rides the existing detail / registry gates — no new permission
surface — so the security matrix here is light (one anon→403 check on
the detail endpoint). The feature-specific assertions are:

- An object-level custom view appears on the detail payload with
  ``level == "object"`` and a reversible ``url`` carrying the object's
  pk.
- A changelist-level custom view appears with ``level == "changelist"``
  and a no-arg ``url``; it also rides through to the registry model
  entry.
- The five standard CRUD routes are NOT surfaced as custom views.
- A plain admin (no custom ``get_urls``) yields no ``custom_views`` key.
- A misbehaving ``get_urls`` never 500s the detail endpoint.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from importlib import import_module
from importlib import reload

import pytest
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.test import Client
from django.urls import clear_url_caches
from django.urls import path

DETAIL_URL = "/admin-react/api/v1/auth/group/{pk}/"
REGISTRY_URL = "/admin-react/api/v1/registry/"


def _report_view(request):  # noqa: ANN001, ANN202
    return HttpResponse("report")


_report_view.short_description = "Group Report"


def _tool_view(request, object_id):  # noqa: ANN001, ANN202, ARG001
    return HttpResponse("tool")


@contextmanager
def custom_get_urls(extra_factory) -> Iterator[None]:  # noqa: ANN001
    """Patch ``GroupAdmin.get_urls`` to prepend ``extra_factory(self)`` routes.

    ``path("admin/", admin.site.urls)`` freezes ``admin.site.get_urls()``
    into the root URLconf's ``urlpatterns`` the first time that module is
    imported (by an earlier request in the suite). To make the patched
    routes reverse-able regardless of suite ordering, we reload the root
    URLconf module (re-evaluating ``admin.site.urls``) and clear the URL
    caches — then undo both on exit so other tests see the pristine wiring.
    """
    model_admin = admin.site._registry[Group]
    original = model_admin.get_urls

    def patched():  # noqa: ANN202
        return list(extra_factory(model_admin)) + original()

    model_admin.get_urls = patched
    root_urlconf = import_module(settings.ROOT_URLCONF)
    reload(root_urlconf)
    clear_url_caches()
    try:
        yield
    finally:
        model_admin.get_urls = original
        reload(root_urlconf)
        clear_url_caches()


@contextmanager
def patch_get_urls(replacement) -> Iterator[None]:  # noqa: ANN001
    """Patch ``GroupAdmin.get_urls`` directly (no URLconf reload).

    For robustness tests that only exercise the package's introspection
    (``custom_views_for`` calls ``get_urls()`` itself) — they never need
    the routes to be reverse-able, so we skip the URLconf reload that
    would otherwise evaluate (and re-raise) a deliberately-broken
    ``get_urls`` at build time.
    """
    model_admin = admin.site._registry[Group]
    original = model_admin.get_urls
    model_admin.get_urls = replacement
    try:
        yield
    finally:
        model_admin.get_urls = original


def _object_and_changelist_routes(model_admin):  # noqa: ANN001, ANN202
    """One changelist-level + one object-level custom route."""
    return [
        path(
            "report/",
            model_admin.admin_site.admin_view(_report_view),
            name="auth_group_report",
        ),
        path(
            "<path:object_id>/send/",
            model_admin.admin_site.admin_view(_tool_view),
            name="auth_group_send",
        ),
    ]


# --------------------------------------------------------------------------- #
# Auth (inherited gate — one representative check)                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_detail_anonymous_forbidden(anon_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    with custom_get_urls(_object_and_changelist_routes):
        response = anon_client.get(DETAIL_URL.format(pk=g.pk))
    assert response.status_code == 403
    # No body leakage — the custom-view payload must never reach an
    # unauthenticated caller.
    assert "custom_views" not in response.json()


# --------------------------------------------------------------------------- #
# Detail payload surfaces custom views                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_detail_exposes_object_and_changelist_custom_views(
    superuser_client: Client,
) -> None:
    g = Group.objects.create(name="alpha")
    with custom_get_urls(_object_and_changelist_routes):
        response = superuser_client.get(DETAIL_URL.format(pk=g.pk))

    assert response.status_code == 200, response.content
    views = response.json()["custom_views"]
    by_name = {v["name"]: v for v in views}

    assert "auth_group_report" in by_name
    assert "auth_group_send" in by_name

    # Object-level: level == "object", url carries this object's pk.
    send = by_name["auth_group_send"]
    assert send["level"] == "object"
    assert send["url"] == f"/admin/auth/group/{g.pk}/send/"

    # Changelist-level: level == "changelist", url takes no object.
    report = by_name["auth_group_report"]
    assert report["level"] == "changelist"
    assert report["url"] == "/admin/auth/group/report/"


@pytest.mark.django_db
def test_label_prefers_short_description_else_humanizes(
    superuser_client: Client,
) -> None:
    g = Group.objects.create(name="alpha")
    with custom_get_urls(_object_and_changelist_routes):
        response = superuser_client.get(DETAIL_URL.format(pk=g.pk))

    by_name = {v["name"]: v for v in response.json()["custom_views"]}
    # ``_report_view.short_description`` wins for the report route.
    assert by_name["auth_group_report"]["label"] == "Group Report"
    # ``_tool_view`` has no short_description → humanized route name.
    assert by_name["auth_group_send"]["label"] == "Auth group send"


@pytest.mark.django_db
def test_standard_crud_routes_not_surfaced(superuser_client: Client) -> None:
    """The five Django CRUD routes must never appear as custom views."""
    g = Group.objects.create(name="alpha")
    with custom_get_urls(_object_and_changelist_routes):
        response = superuser_client.get(DETAIL_URL.format(pk=g.pk))

    names = {v["name"] for v in response.json()["custom_views"]}
    for standard in (
        "auth_group_changelist",
        "auth_group_add",
        "auth_group_change",
        "auth_group_delete",
        "auth_group_history",
    ):
        assert standard not in names


# --------------------------------------------------------------------------- #
# Plain admin (no custom get_urls) → no key at all                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_plain_admin_has_no_custom_views_key(superuser_client: Client) -> None:
    g = Group.objects.create(name="alpha")
    response = superuser_client.get(DETAIL_URL.format(pk=g.pk))
    assert response.status_code == 200, response.content
    assert "custom_views" not in response.json()


# --------------------------------------------------------------------------- #
# Registry surfaces changelist-level custom views only                        #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_registry_surfaces_changelist_level_only(superuser_client: Client) -> None:
    with custom_get_urls(_object_and_changelist_routes):
        response = superuser_client.get(REGISTRY_URL)

    assert response.status_code == 200, response.content
    entry = _find_group_entry(response.json())
    assert entry is not None
    views = entry.get("custom_views", [])
    names = {v["name"] for v in views}
    # Changelist-level route rides through; object-level does NOT (no
    # object to anchor it to in the registry context).
    assert "auth_group_report" in names
    assert "auth_group_send" not in names
    assert all(v["level"] == "changelist" for v in views)


@pytest.mark.django_db
def test_registry_plain_admin_no_custom_views_key(superuser_client: Client) -> None:
    response = superuser_client.get(REGISTRY_URL)
    assert response.status_code == 200, response.content
    entry = _find_group_entry(response.json())
    assert entry is not None
    assert "custom_views" not in entry


# --------------------------------------------------------------------------- #
# Robustness: a misbehaving get_urls must never 500                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_misbehaving_get_urls_does_not_500(superuser_client: Client) -> None:
    g = Group.objects.create(name="alpha")

    def boom():  # noqa: ANN202
        raise RuntimeError("consumer get_urls blew up")

    with patch_get_urls(boom):
        response = superuser_client.get(DETAIL_URL.format(pk=g.pk))

    # Degrades cleanly: a 200 detail with no custom_views key, not a 500.
    assert response.status_code == 200, response.content
    assert "custom_views" not in response.json()


@pytest.mark.django_db
def test_unreversible_custom_route_skipped(superuser_client: Client) -> None:
    """A named custom route that can't reverse is silently dropped.

    Here the route declares a second capture group the package never
    fills, so ``reverse(..., args=[pk])`` raises → the route is skipped
    rather than 500-ing the endpoint.
    """
    g = Group.objects.create(name="alpha")

    def two_arg_route(model_admin):  # noqa: ANN001, ANN202
        return [
            path(
                "<path:object_id>/x/<int:other>/",
                model_admin.admin_site.admin_view(_tool_view),
                name="auth_group_twoarg",
            ),
        ]

    with custom_get_urls(two_arg_route):
        response = superuser_client.get(DETAIL_URL.format(pk=g.pk))

    assert response.status_code == 200, response.content
    # Either no key (only route dropped) or, if present, our route is absent.
    names = {v["name"] for v in response.json().get("custom_views", [])}
    assert "auth_group_twoarg" not in names


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _find_group_entry(registry_payload: dict):  # noqa: ANN001, ANN202
    """Locate the ``auth.group`` model entry in a registry response."""
    for app in registry_payload.get("apps", []):
        for model in app.get("models", []):
            if model.get("real_app_label") == "auth" and model.get("model_name") == "group":
                return model
    return None
