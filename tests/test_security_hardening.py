"""Defense-in-depth tests for #88 + #89 + #93.

Wire contract: ``docs/api-contract.md`` §3.3 (filter descriptors) +
the URL-reservation guard in ``api/registry.py::resolve_model``.

Covered:

- **#88** Sensitive-name denylist on filter descriptors:
  - A field-based filter with a sensitive name (``password``,
    ``api_key``, …) is dropped from ``filters[]``.
  - A ``SimpleListFilter`` whose ``parameter_name`` is sensitive is
    likewise dropped.

- **#89** Unregistered-FK leak guard:
  - ``_spec_for_fk`` returns ``None`` when the related model isn't
    in the configured admin site's registry — the entry is dropped
    rather than emitting a ``to: {app_label, model_name}`` for an
    unregistered model.
  - When the related model IS registered, the descriptor includes
    ``to:`` as before (regression guard).

- **#93** Reserved-app-label routing:
  - ``resolve_model`` returns ``None`` for ``app_label`` in
    ``RESERVED_APP_LABELS`` even when a consumer has a Django app
    with that exact label. The endpoint emits 404 (no oracle).
"""

from __future__ import annotations

import pytest
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.test import Client

from django_admin_react.api.filters import _spec_for_fk
from django_admin_react.api.filters import filters_payload
from django_admin_react.api.registry import RESERVED_APP_LABELS
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from tests.helpers import admin_override


# --------------------------------------------------------------------------- #
# #88 — Sensitive-name denylist on filter descriptors                         #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_sensitive_field_name_dropped_from_filters(rf, staff_client: Client) -> None:
    """A consumer admin declaring ``list_filter = ('password',)`` must
    not leak the field name on the wire."""
    request = rf.get("/")
    request.user = staff_client.session["_auth_user_id"] and User.objects.first()
    with admin_override(
        Group,
        get_list_filter=lambda self, request: ("password", "name"),
    ):
        group_admin = admin.site._registry[Group]
        out = filters_payload(group_admin, request, admin_site=admin.site)
    names = [d["name"] for d in out]
    assert "password" not in names
    # The other entries on the same admin keep working.
    # (``name`` is a CharField with no choices and isn't bool/FK/date,
    # so it falls through silently; that's the existing behavior.)


class _SecretFilter(SimpleListFilter):
    """Inline SimpleListFilter whose parameter_name matches the denylist."""

    title = "Secret"
    parameter_name = "api_key"

    def lookups(self, request, model_admin):
        return [("a", "A"), ("b", "B")]

    def queryset(self, request, queryset):
        return queryset


@pytest.mark.django_db
def test_sensitive_simple_filter_parameter_name_dropped(rf, staff_client: Client) -> None:
    """A custom ``SimpleListFilter`` whose ``parameter_name`` hits the
    denylist (``api_key``) is dropped from descriptor output."""
    request = rf.get("/")
    with admin_override(
        Group,
        get_list_filter=lambda self, request: (_SecretFilter,),
    ):
        group_admin = admin.site._registry[Group]
        out = filters_payload(group_admin, request, admin_site=admin.site)
    assert all(d["name"] != "api_key" for d in out)


# --------------------------------------------------------------------------- #
# #89 — Unregistered-FK leak guard                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_fk_filter_dropped_when_target_unregistered(rf) -> None:
    """``_spec_for_fk`` returns ``None`` when the related model isn't
    in the admin site's registry.

    Uses ``auth.Permission.content_type`` (FK to
    ``contenttypes.ContentType``). ``ContentType`` is *not* admin-
    registered by default in the test project, so the spec must drop
    the descriptor — no ``to: {contenttypes, contenttype}`` leak.
    """
    from django.contrib.auth.models import Permission

    request = rf.get("/")
    field = Permission._meta.get_field("content_type")
    spec = _spec_for_fk("content_type", field, request, admin_site=admin.site)
    assert spec is None


@pytest.mark.django_db
def test_fk_filter_kept_when_target_registered(rf) -> None:
    """Regression guard: when the FK target IS registered (Group →
    via admin), the descriptor still emits with the ``to:`` block."""
    # auth.User → groups M2M, not FK. So we need an FK to a registered
    # model. auth.User itself is registered. Build a synthetic FK
    # field reference using Permission.content_type → ContentType,
    # but register ContentType first.
    from django.contrib.contenttypes.admin import GenericTabularInline  # noqa: F401
    from django.contrib.contenttypes.models import ContentType

    if ContentType not in admin.site._registry:
        admin.site.register(ContentType)
    try:
        from django.contrib.auth.models import Permission

        request = rf.get("/")
        field = Permission._meta.get_field("content_type")
        spec = _spec_for_fk("content_type", field, request, admin_site=admin.site)
        assert spec is not None
        assert spec["type"] == "foreignkey"
        assert spec["to"]["app_label"] == "contenttypes"
        assert spec["to"]["model_name"] == "contenttype"
    finally:
        admin.site.unregister(ContentType)


# --------------------------------------------------------------------------- #
# #93 — Reserved-app-label routing                                            #
# --------------------------------------------------------------------------- #
def test_reserved_app_labels_constant_contents() -> None:
    """The reserved set covers every top-level URL segment the
    package mounts directly under ``/api/v1/`` (so a consumer with
    ``app_label`` matching any of these never shadows the package)."""
    assert "registry" in RESERVED_APP_LABELS
    assert "schema" in RESERVED_APP_LABELS
    assert "session" in RESERVED_APP_LABELS


@pytest.mark.django_db
def test_resolve_model_returns_none_for_reserved_app_label(rf) -> None:
    """``resolve_model`` returns ``None`` for any reserved app label,
    regardless of whether a consumer happens to register a model
    with that label."""
    request = rf.get("/")
    admin_site = get_admin_site()
    for reserved in RESERVED_APP_LABELS:
        assert resolve_model(admin_site, request, reserved, "anything") is None


@pytest.mark.django_db
def test_resolve_model_reserved_check_is_case_insensitive(rf) -> None:
    """``Session`` / ``SESSION`` / ``session`` all hit the reserved
    guard (mirrors the existing case-insensitive lookup of the rest
    of ``resolve_model``)."""
    request = rf.get("/")
    admin_site = get_admin_site()
    for variant in ("session", "Session", "SESSION", "SeSsIoN"):
        assert resolve_model(admin_site, request, variant, "foo") is None


@pytest.mark.django_db
def test_list_endpoint_404s_on_reserved_segment(staff_client: Client) -> None:
    """End-to-end: a request to ``/api/v1/session/foo/`` returns 404
    (the canonical ``not_found`` envelope) — no oracle disclosing
    whether a consumer has a ``session`` app or not."""
    response = staff_client.get("/admin-react/api/v1/session/foo/")
    assert response.status_code == 404


@pytest.fixture
def rf():
    """Lightweight RequestFactory fixture."""
    from django.test import RequestFactory

    return RequestFactory()
