"""Tests for ``GET /api/v1/registry/`` honoring ``AdminSite.get_app_list``.

Closes [issue #138](https://github.com/MartinCastroAlvarez/django-admin-react/issues/138);
contract documented in [PR #140](https://github.com/MartinCastroAlvarez/django-admin-react/pull/140)
(``docs/api-contract.md`` §2).

Coverage:

- **Default site**: the existing shape continues to work, with new
  fields (``name`` / ``is_group`` / ``real_app_label``) populated
  from Django's stock ``get_app_list``.
- **Synthetic groups**: a custom ``AdminSite`` override regrouping
  models into operator-meaningful sections (``"Loans"``,
  ``"Configuration"``) — the registry response surfaces those groups
  with ``is_group: true`` and each model carries the real
  ``real_app_label`` so URL construction stays correct.
- **Permission filtering inheritance**: ``get_app_list`` already
  filters by ``has_module_permission`` + ``has_view_permission``;
  the registry payload inherits that. Verified by overriding the
  per-model permission and confirming the group surfaces fewer
  entries (or none).
- **Alphabetical sort**: Django's default ``get_app_list`` sorts
  apps by ``name.lower()`` and models within each app — the registry
  payload inherits that, closing the side-effect part of
  [issue #136](https://github.com/MartinCastroAlvarez/django-admin-react/issues/136).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.test import Client

REGISTRY_URL = "/admin-react/api/v1/registry/"


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
@contextmanager
def _model_admin_override(model_cls, **method_returns) -> Iterator[None]:
    """Temporarily override ``has_*_permission`` on a registered ModelAdmin.

    Mirrors the helper in ``tests/test_registry.py`` — duplicated here
    to keep this file self-contained.
    """
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
# Default AdminSite — existing shape + new fields populated                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_default_site_carries_new_fields(superuser_client: Client) -> None:
    """Default ``admin.site`` — response shape carries the new fields
    (``name``, ``is_group``, ``verbose_name``) on each ``apps[]`` entry
    and ``real_app_label`` on each model entry, with sensible values.
    """
    response = superuser_client.get(REGISTRY_URL)
    assert response.status_code == 200
    payload = response.json()

    # The auth app is always present for the default site fixture.
    auth_app = next((a for a in payload["apps"] if a["app_label"] == "auth"), None)
    assert auth_app is not None, "auth app missing from registry payload"

    # New per-app fields.
    assert "name" in auth_app
    assert "verbose_name" in auth_app
    assert "is_group" in auth_app
    assert auth_app["is_group"] is False, "auth.* is a real Django app — is_group must be False"
    # name and verbose_name should be the same on default site (both
    # come from get_app_list's "name" key, which Django populates from
    # apps.get_app_config(label).verbose_name).
    assert auth_app["name"] == auth_app["verbose_name"]

    # New per-model fields.
    for model_entry in auth_app["models"]:
        assert "real_app_label" in model_entry
        assert model_entry["real_app_label"] == "auth"
        # On the default site, the group's app_label == real_app_label.
        assert model_entry["app_label"] == "auth"


@pytest.mark.django_db
def test_default_site_models_sorted_alphabetically(superuser_client: Client) -> None:
    """Django's default ``get_app_list`` sorts apps by ``name.lower()``
    and models within each app — the registry inherits that.

    Side-effect close of [#136](https://github.com/MartinCastroAlvarez/django-admin-react/issues/136).
    """
    response = superuser_client.get(REGISTRY_URL)
    payload = response.json()

    # Apps must be sorted by name (case-insensitive). Compare to the
    # actual sequence returned.
    app_names_lower = [a["name"].lower() for a in payload["apps"]]
    assert app_names_lower == sorted(
        app_names_lower
    ), "apps[] must be sorted by name.lower() per Django get_app_list"

    # Models within auth must be sorted by entry name (Django's
    # get_app_list populates name from verbose_name_plural).
    auth_app = next(a for a in payload["apps"] if a["app_label"] == "auth")
    model_names = [m["verbose_name_plural"] for m in auth_app["models"]]
    # Django's default sort key is the get_app_list entry's "name".
    # The package emits "verbose_name_plural" from _model_entry which
    # equals that key. Assert the order is monotonic.
    assert model_names == sorted(
        model_names, key=lambda s: s.lower()
    ), f"models within auth must be sorted alphabetically; got {model_names}"


# --------------------------------------------------------------------------- #
# Custom AdminSite — synthetic groups honored                                 #
# --------------------------------------------------------------------------- #
class _GroupedAdminSite(AdminSite):
    """An AdminSite that regroups models under synthetic group names.

    Models are looked up by ``(real_app_label, object_name)`` in
    ``_registry`` so the test is robust to registration order.
    """

    def get_app_list(self, request, app_label=None):  # noqa: ARG002
        # Use Django's default to harvest the per-model "model" key and
        # permission filtering, then rebuild under synthetic groups.
        default = super().get_app_list(request, app_label=app_label)
        model_lookup = {}
        for app in default:
            for m in app["models"]:
                model_lookup[(app["app_label"], m["object_name"])] = m

        groups = [
            ("Accounts", "accounts", [("auth", "User")]),
            ("Configuration", "configuration", [("auth", "Group")]),
        ]
        out = []
        for group_name, group_label, members in groups:
            group_models = [model_lookup[key] for key in members if key in model_lookup]
            if group_models:
                out.append(
                    {
                        "name": group_name,
                        "app_label": group_label,
                        "app_url": "",
                        "has_module_perms": True,
                        "models": group_models,
                    }
                )
        return out


@pytest.fixture
def grouped_admin_site_settings(settings, db):  # noqa: ARG001 — db forces DB
    """Wire ``DJANGO_ADMIN_REACT["ADMIN_SITE"]`` to a ``_GroupedAdminSite``.

    The custom site **shares the default site's ``_registry``** by direct
    reference, so:

    1. Every model registered on ``admin.site`` is visible through the
       custom site without re-registration (avoids the
       ``AlreadyRegistered`` trap).
    2. Any per-model permission override done via
       :func:`_model_admin_override` (which targets ``admin.site._registry``)
       takes effect on the custom site as well — same dict, same
       ``ModelAdmin`` instances.

    Also clears ``django_admin_react.conf._cached`` before and after so
    the package's lazy settings reader actually re-reads
    ``settings.DJANGO_ADMIN_REACT`` (the cache otherwise pins the first
    value seen in the test process).
    """
    from django_admin_react import conf

    site = _GroupedAdminSite(name="grouped")
    site._registry = admin.site._registry  # share by reference

    # Stash on the module-level test marker so we can dotted-path it.
    import sys

    module = sys.modules[__name__]
    module._test_grouped_site = site
    settings.DJANGO_ADMIN_REACT = {
        "ADMIN_SITE": f"{__name__}._test_grouped_site",
    }
    conf._cached = None  # force conf to re-resolve on next access
    try:
        yield site
    finally:
        conf._cached = None  # restore default for subsequent tests


@pytest.mark.django_db
def test_custom_site_synthetic_groups_carry_is_group_true(
    superuser_client: Client, grouped_admin_site_settings
) -> None:
    """A custom ``AdminSite`` that regroups models into synthetic
    sections surfaces ``is_group: true`` for each group and the right
    ``real_app_label`` on each model entry.
    """
    response = superuser_client.get(REGISTRY_URL)
    assert response.status_code == 200
    payload = response.json()

    # The default Django app labels should not appear at top level.
    top_labels = {a["app_label"] for a in payload["apps"]}
    assert "auth" not in top_labels, "auth.* leaked through synthetic grouping"

    # The synthetic groups should be present.
    assert "accounts" in top_labels
    assert "configuration" in top_labels

    accounts_group = next(a for a in payload["apps"] if a["app_label"] == "accounts")
    assert accounts_group["is_group"] is True
    assert accounts_group["name"] == "Accounts"

    # Each model in the synthetic group keeps its real_app_label so the
    # SPA can construct URLs at <mount>/api/v1/<real_app_label>/<model>/.
    for m in accounts_group["models"]:
        assert "real_app_label" in m
        # accounts group → User → real_app_label "auth"
        if m["object_name"] == "User":
            assert m["real_app_label"] == "auth"
            assert (
                m["app_label"] == "accounts"
            ), "model entry's app_label should match the surrounding group"


@pytest.mark.django_db
def test_custom_site_group_filtered_by_view_permission(
    superuser_client: Client, grouped_admin_site_settings
) -> None:
    """When the user lacks ``has_view_permission`` on a model in a
    synthetic group, Django's ``get_app_list`` drops it — and the
    registry payload inherits the filter (no parallel gate).
    """

    def deny(self, request, obj=None) -> bool:  # noqa: ARG001
        return False

    # Override on the default-site ModelAdmin since the custom site
    # reuses the same _registry.
    with _model_admin_override(User, has_view_permission=deny):
        response = superuser_client.get(REGISTRY_URL)

    assert response.status_code == 200
    payload = response.json()

    accounts_group = next((a for a in payload["apps"] if a["app_label"] == "accounts"), None)
    # Django's get_app_list drops apps whose models list is empty after
    # filtering — so the synthetic group may be absent entirely. If
    # present, it must not contain User.
    if accounts_group is not None:
        object_names = {m["object_name"] for m in accounts_group["models"]}
        assert (
            "User" not in object_names
        ), "User must be hidden when has_view_permission returns False"
