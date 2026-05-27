"""Tests for the SPA index view at the package's mount URL.

The view serves the React shell HTML to staff. It is the only
non-API view in the package, and it enforces the same auth gate
the API uses (rule 1 in ``SECURITY.md`` §3).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import pytest
from django.contrib.admin import site as default_admin_site
from django.test import Client
from django.test import override_settings

import django_admin_react.views as views_module
from django_admin_react import views
from django_admin_react import views as spa_views

ROOT_URL = "/admin-react/"


@pytest.fixture(autouse=True)
def _clear_manifest_cache() -> None:
    """The view caches the manifest in-process; isolate each test."""
    views._load_manifest_entry.cache_clear()  # type: ignore[attr-defined]


@pytest.fixture
def fake_manifest(tmp_path: Path) -> Path:
    """Drop a fake Vite manifest into the package's static dir for the test.

    Uses ``mock.patch`` on the module-level path constant so we
    don't actually write into the shipped package on disk.
    """
    manifest_body = {
        "index.html": {
            "file": "assets/index-abc.js",
            "name": "index",
            "isEntry": True,
            "css": ["assets/index-abc.css"],
        }
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_body))
    with mock.patch.object(views_module, "_MANIFEST_PATH", manifest_path):
        views._load_manifest_entry.cache_clear()  # type: ignore[attr-defined]
        yield manifest_path
    views._load_manifest_entry.cache_clear()  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Auth gate                                                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_redirected_to_login(anon_client: Client) -> None:
    response = anon_client.get(ROOT_URL)
    assert response.status_code == 302
    # The package leaves LOGIN_URL up to the consumer's settings — only
    # assert that the redirect carries the SPA path as the ``next``
    # parameter so the user lands back here after login. The ``next``
    # value is percent-encoded (CodeQL py/url-redirection fix), so the
    # raw path appears encoded in Location; decode the query to compare.
    location = response["Location"]
    assert "next=" in location
    query = parse_qs(urlsplit(location).query)
    assert query["next"][0].startswith(ROOT_URL)


@pytest.mark.django_db
def test_authenticated_non_staff_redirected(user_client: Client) -> None:
    """Non-staff users do not see the SPA, even if logged in."""
    response = user_client.get(ROOT_URL)
    # The package treats them like anonymous for the SPA — same redirect
    # path. (The API returns 403, but the SPA shell is a UI surface and
    # bouncing through login is the friendlier flow.)
    assert response.status_code == 302
    assert "next=" in response["Location"]


@pytest.mark.django_db
def test_superuser_receives_spa_html(superuser_client: Client) -> None:
    response = superuser_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert '<div id="root">' in body
    # CSRF cookie must be set so the SPA can read it before unsafe calls.
    assert "csrftoken" in response.cookies


@pytest.mark.django_db
def test_spa_shell_is_not_cacheable(superuser_client: Client) -> None:
    """The HTML shell references the hash-named bundle, so it must never
    be cached — a stale shell points at an asset filename that no longer
    exists after a rebuild, booting a broken/old SPA. (Hashed assets
    themselves stay cacheable; only this entrypoint must revalidate.)
    """
    response = superuser_client.get(ROOT_URL)
    cache_control = response.headers.get("Cache-Control", "")
    assert (
        "no-cache" in cache_control or "no-store" in cache_control
    ), f"SPA shell must send no-cache/no-store; got {cache_control!r}"


# --------------------------------------------------------------------------- #
# Mount detection                                                             #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_mount_meta_tag_reflects_url(superuser_client: Client) -> None:
    response = superuser_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="dar-mount"' in body
    assert 'content="/admin-react/"' in body


# --------------------------------------------------------------------------- #
# Bundle wiring                                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_with_manifest_includes_bundle_tags(superuser_client: Client, fake_manifest: Path) -> None:
    response = superuser_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "assets/index-abc.js" in body
    assert "assets/index-abc.css" in body
    assert 'rel="stylesheet"' in body
    assert 'type="module"' in body


@pytest.mark.django_db
def test_without_manifest_renders_helpful_fallback(
    superuser_client: Client, tmp_path: Path
) -> None:
    """Point the view at a non-existent manifest to force the dev fallback."""
    missing = tmp_path / "missing-manifest.json"
    with mock.patch.object(views_module, "_MANIFEST_PATH", missing):
        views._load_manifest_entry.cache_clear()  # type: ignore[attr-defined]
        response = superuser_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # The "build the SPA" instruction must be visible so a contributor
    # who runs `runserver` without `pnpm build:vite` knows what to do.
    assert "pnpm" in body
    assert "build:vite" in body


# --------------------------------------------------------------------------- #
# Branding (BRAND_TITLE + BRAND_LOGO_URL)                                     #
# --------------------------------------------------------------------------- #
def _reload_conf() -> None:
    """Force `django_admin_react.conf` to re-read settings."""
    import django_admin_react.conf as _conf

    importlib.reload(_conf)
    # SpaIndexView holds a module-level reference to conf — re-bind.
    importlib.reload(spa_views)


@pytest.mark.django_db
def test_brand_title_falls_back_to_admin_site_header(superuser_client: Client) -> None:
    """When `BRAND_TITLE` is unset, the SPA shell uses the configured
    AdminSite's `site_header`. Consumers who already customised their
    AdminSite for the legacy admin don't need a second setting.
    """
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        original_header = default_admin_site.site_header
        default_admin_site.site_header = "Operations Console"
        try:
            response = superuser_client.get(ROOT_URL)
            html = response.content.decode("utf-8")
            assert 'name="dar-brand-title" content="Operations Console"' in html
            assert "<title>Operations Console</title>" in html
        finally:
            default_admin_site.site_header = original_header


@pytest.mark.django_db
def test_brand_title_explicit_override_wins(superuser_client: Client) -> None:
    """`BRAND_TITLE` overrides the AdminSite's `site_header`."""
    with override_settings(DJANGO_ADMIN_REACT={"BRAND_TITLE": "Acme"}):
        _reload_conf()
        original_header = default_admin_site.site_header
        default_admin_site.site_header = "Something Else"
        try:
            response = superuser_client.get(ROOT_URL)
            html = response.content.decode("utf-8")
            assert 'name="dar-brand-title" content="Acme"' in html
            assert "<title>Acme</title>" in html
        finally:
            default_admin_site.site_header = original_header


@pytest.mark.django_db
def test_primary_color_default_injected(superuser_client: Client) -> None:
    """The accent color is injected as the `--dar-primary` CSS variable;
    the default is blue-600 (#437)."""
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        html = superuser_client.get(ROOT_URL).content.decode("utf-8")
        assert "--dar-primary: #2563eb;" in html


@pytest.mark.django_db
def test_primary_color_valid_hex_override(superuser_client: Client) -> None:
    """A valid hex `PRIMARY_COLOR` is reflected in `--dar-primary` (#437)."""
    with override_settings(DJANGO_ADMIN_REACT={"PRIMARY_COLOR": "#ff8800"}):
        _reload_conf()
        html = superuser_client.get(ROOT_URL).content.decode("utf-8")
        assert "--dar-primary: #ff8800;" in html


@pytest.mark.django_db
def test_primary_color_non_hex_value_cannot_inject_css(superuser_client: Client) -> None:
    """A non-hex `PRIMARY_COLOR` can't break out of the `<style>` block —
    it's rejected and the default is used, so no CSS injection (#437)."""
    evil = "red; } body { display: none } :root {"
    with override_settings(DJANGO_ADMIN_REACT={"PRIMARY_COLOR": evil}):
        _reload_conf()
        html = superuser_client.get(ROOT_URL).content.decode("utf-8")
        assert "display: none" not in html
        assert "--dar-primary: #2563eb;" in html


@pytest.mark.django_db
def test_brand_logo_url_renders_favicon_and_meta(superuser_client: Client) -> None:
    """`BRAND_LOGO_URL` populates both the `<link rel="icon">` and the
    `dar-brand-logo` meta tag the SPA reads at boot.
    """
    logo_url = "/static/acme/logo.svg"
    with override_settings(DJANGO_ADMIN_REACT={"BRAND_LOGO_URL": logo_url}):
        _reload_conf()
        response = superuser_client.get(ROOT_URL)
        html = response.content.decode("utf-8")
        assert f'name="dar-brand-logo" content="{logo_url}"' in html
        assert f'rel="icon" href="{logo_url}"' in html


@pytest.mark.django_db
def test_brand_logo_url_unset_falls_back_to_data_uri(superuser_client: Client) -> None:
    """When `BRAND_LOGO_URL` is unset, the no-op `data:,` placeholder
    is preserved (matches the prior hardcoded behaviour)."""
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        response = superuser_client.get(ROOT_URL)
        html = response.content.decode("utf-8")
        assert 'rel="icon" href="data:,"' in html
        assert 'name="dar-brand-logo"' not in html


# --------------------------------------------------------------------------- #
# Dark-mode no-flash: server-side `.dark` from the `dar-theme` cookie (#84)    #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_dark_theme_cookie_paints_dark_class_on_html(superuser_client: Client) -> None:
    """A `dar-theme=dark` cookie makes the shell render `<html class="dark">`
    so the page is dark at first paint — no flash, no inline script."""
    superuser_client.cookies["dar-theme"] = "dark"
    html = superuser_client.get(ROOT_URL).content.decode("utf-8")
    assert '<html lang="en" class="dark">' in html


@pytest.mark.django_db
def test_no_theme_cookie_paints_no_dark_class(superuser_client: Client) -> None:
    """Without the cookie the shell paints its default (light) — the JS
    reconciles the effective theme on load."""
    html = superuser_client.get(ROOT_URL).content.decode("utf-8")
    assert '<html lang="en">' in html
    assert 'class="dark"' not in html


@pytest.mark.django_db
def test_light_theme_cookie_paints_no_dark_class(superuser_client: Client) -> None:
    """`dar-theme=light` keeps the default light shell (the class is only
    added for dark)."""
    superuser_client.cookies["dar-theme"] = "light"
    html = superuser_client.get(ROOT_URL).content.decode("utf-8")
    assert 'class="dark"' not in html


@pytest.mark.django_db
def test_invalid_theme_cookie_is_ignored(superuser_client: Client) -> None:
    """A cookie value outside {light,dark} is ignored: `_resolve_initial_theme`
    returns None, so no dark class — and since the value is only ever
    *compared* in the template (never output), it can't reach the HTML."""
    superuser_client.cookies["dar-theme"] = "totally-bogus-value"
    html = superuser_client.get(ROOT_URL).content.decode("utf-8")
    assert 'class="dark"' not in html
    assert "totally-bogus-value" not in html


# --------------------------------------------------------------------------- #
# REACT_LOGIN — serve the shell to anonymous users (Issue #167)               #
# --------------------------------------------------------------------------- #
def test_react_login_off_anon_still_redirected(anon_client: Client) -> None:
    """Default (REACT_LOGIN unset): anonymous → 302 to the login page."""
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        try:
            response = anon_client.get(ROOT_URL)
            assert response.status_code == 302
        finally:
            _reload_conf()


def test_react_login_on_anon_gets_shell_not_redirect(
    anon_client: Client, fake_manifest: Path
) -> None:
    """REACT_LOGIN=True: anonymous gets the SPA shell (200) + CSRF cookie.

    The React app then renders its own login form (Issue #167). The
    shell carries no user data, so serving it to an anonymous user is
    safe — every data API call still 403s until they authenticate.
    """
    with override_settings(DJANGO_ADMIN_REACT={"REACT_LOGIN": True}):
        _reload_conf()
        try:
            response = anon_client.get(ROOT_URL)
            assert response.status_code == 200
            # CSRF cookie issued so the login POST can carry X-CSRFToken.
            assert "csrftoken" in response.cookies
            # The shell must not leak any authenticated-user data.
            body = response.content.decode("utf-8", errors="replace").lower()
            assert "is_superuser" not in body
        finally:
            _reload_conf()


def test_react_login_on_does_not_change_staff_path(superuser_client: Client) -> None:
    """REACT_LOGIN=True doesn't alter the authenticated-staff behavior."""
    with override_settings(DJANGO_ADMIN_REACT={"REACT_LOGIN": True}):
        _reload_conf()
        try:
            response = superuser_client.get(ROOT_URL)
            assert response.status_code == 200
        finally:
            _reload_conf()


@pytest.mark.django_db
def test_shell_links_pwa_manifest(superuser_client: Client) -> None:
    """The SPA shell links the package-served manifest so the browser
    offers "Install" (#86 frontend). Mount-relative href."""
    body = superuser_client.get(ROOT_URL).content.decode("utf-8")
    assert 'rel="manifest"' in body
    assert 'href="/admin-react/web.manifest"' in body
    assert 'name="theme-color"' in body


@pytest.mark.django_db
def test_shell_does_not_leak_raw_template_syntax(superuser_client: Client) -> None:
    """The rendered shell must never contain raw template syntax.

    Regression: a multi-line ``{# ... #}`` comment in the template leaked
    verbatim into the page head — the hash-comment form is single-line
    only, so Django renders a multi-line one as literal text. Block-tag
    ``{% comment %}`` comments are stripped; assert no comment/tag/var
    delimiters survive into the served HTML.
    """
    body = superuser_client.get(ROOT_URL).content.decode("utf-8")
    for token in ("{#", "#}", "{%", "%}", "{{", "}}"):
        assert token not in body, f"raw template syntax {token!r} leaked into the shell"
