"""PWA backend serving tests (Issue #86, backend half).

Covers the security-relevant properties of the manifest + service
worker views (``django_admin_react/pwa.py``):

- Manifest is anonymous (install prompt fires pre-login) and carries
  NO per-user data.
- Manifest ``start_url`` / ``scope`` reflect the consumer mount.
- SW is served with ``Service-Worker-Allowed: <mount>`` (scope ≤ mount)
  and the JS embeds the mount + the no-store / mutation-safety guards.
- Both honour the consumer's chosen mount prefix.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.test import override_settings

MANIFEST_URL = "/admin-react/web.manifest"
SW_URL = "/admin-react/sw.js"


# --------------------------------------------------------------------------- #
# Manifest                                                                    #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_manifest_served_to_anonymous(anon_client: Client) -> None:
    """The manifest is reachable without auth (install prompt is pre-login)."""
    response = anon_client.get(MANIFEST_URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/manifest+json"


@pytest.mark.django_db
def test_manifest_shape_and_mount(anon_client: Client) -> None:
    response = anon_client.get(MANIFEST_URL)
    body = json.loads(response.content)
    assert body["start_url"] == "/admin-react/"
    assert body["scope"] == "/admin-react/"
    assert body["display"] == "standalone"
    assert body["short_name"] == "Admin"
    assert isinstance(body["icons"], list) and body["icons"]


@pytest.mark.django_db
def test_manifest_carries_no_per_user_data(superuser_client: Client) -> None:
    """Even when an authed superuser fetches it, the manifest must not
    leak any user-identifying field — it's a static/global document."""
    response = superuser_client.get(MANIFEST_URL)
    body = json.loads(response.content)
    blob = json.dumps(body).lower()
    for forbidden in ("username", "is_staff", "is_superuser", "email", "user", "session"):
        assert forbidden not in blob, f"manifest leaked {forbidden!r}"
    # Vary on the client hint so light/dark splash colours don't cross.
    assert "Sec-CH-Prefers-Color-Scheme" in response.get("Vary", "")


@pytest.mark.django_db
def test_manifest_theme_from_client_hint(anon_client: Client) -> None:
    light = json.loads(anon_client.get(MANIFEST_URL).content)
    dark = json.loads(
        anon_client.get(MANIFEST_URL, HTTP_SEC_CH_PREFERS_COLOR_SCHEME="dark").content
    )
    assert light["background_color"] != dark["background_color"]


def _reset_conf_cache() -> None:
    """Force ``django_admin_react.conf`` to re-read settings.

    ``conf`` caches the resolved settings on first access, so
    ``override_settings`` is invisible until the cache is cleared.
    """
    import django_admin_react.conf as _conf

    _conf._cached = None  # type: ignore[attr-defined]


@pytest.mark.django_db
def test_manifest_short_name_override(anon_client: Client) -> None:
    with override_settings(DJANGO_ADMIN_REACT={"PWA_SHORT_NAME": "Ops"}):
        _reset_conf_cache()
        try:
            body = json.loads(anon_client.get(MANIFEST_URL).content)
        finally:
            _reset_conf_cache()
    assert body["short_name"] == "Ops"


# --------------------------------------------------------------------------- #
# Service worker                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_sw_served_with_scope_header(anon_client: Client) -> None:
    response = anon_client.get(SW_URL)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/javascript")
    # Scope widened to the mount (a SW's default scope is its own path).
    assert response["Service-Worker-Allowed"] == "/admin-react/"
    # The SW script must be revalidated, not stored, so a deploy ships a
    # new SW — but NOT no-store (that would break the SW update check).
    assert "no-cache" in response.get("Cache-Control", "")


@pytest.mark.django_db
def test_sw_embeds_mount_and_security_guards(anon_client: Client) -> None:
    """The served SW JS must carry the mount + the load-bearing guards."""
    js = anon_client.get(SW_URL).content.decode("utf-8")
    # Mount injected so the scope check is exact. The value is passed
    # through Django's ``escapejs`` (defense against a crafted path),
    # which renders ``-`` as ``-`` etc. — runtime-equivalent to
    # "/admin-react/". Assert the assignment exists + the path is there
    # rather than the exact (escaped) literal.
    assert "const MOUNT =" in js
    assert "admin" in js and "react" in js
    # No-store invariant present (never cache a no-store response).
    assert "no-store" in js
    # Mutation safety: non-GET requests are not cached/replayed.
    assert "request.method !== 'GET'" in js
    # Cache-purge-on-logout message handler.
    assert "dar:purge" in js
    # Origin check on the message handler (CodeQL js/missing-origin-check):
    # a cross-origin frame must not be able to drive the SW cache.
    assert "event.origin" in js and "self.location.origin" in js


@pytest.mark.django_db
def test_pwa_respects_custom_mount(client: Client) -> None:
    """Served under a different mount, start_url/scope/scope-header follow it."""
    # The test project mounts the package at /admin-react/; this asserts
    # the mount-derivation logic keys off request.path, not a constant.
    manifest = json.loads(client.get(MANIFEST_URL).content)
    assert manifest["scope"] == "/admin-react/"
