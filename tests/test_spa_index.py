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
def test_anonymous_user_gets_shell_under_react_login_default(anon_client: Client) -> None:
    """Default mode (`REACT_LOGIN=True`, the post-2026-05-28 default):
    anonymous users get the React shell so the in-SPA login form renders
    — replacing the legacy admin login URL surface end-to-end. The shell
    carries no user data; every API call still 403s until the user is
    authenticated."""
    response = anon_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # The shell is what's served (not a redirect).
    assert 'name="dar-mount"' in body


@pytest.mark.django_db
def test_authenticated_non_staff_gets_shell_under_react_login_default(user_client: Client) -> None:
    """Non-staff users get the React shell under the new `REACT_LOGIN=True`
    default; the in-SPA login form re-renders for them and the API still
    403s every wire call so no data leaks. (The shell is purely chrome —
    serving it to a non-staff session discloses nothing the static bundle
    wouldn't.)"""
    response = user_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="dar-mount"' in body


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


@pytest.mark.django_db
def test_api_prefix_meta_defaults_to_mount_plus_api_v1(superuser_client: Client) -> None:
    """Default (no `API_URL_PREFIX` override): the `dar-api-prefix` meta
    is `<mount>/api/v1/` — the inline-include URL the package already
    serves, unchanged from before #559."""
    response = superuser_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="dar-api-prefix"' in body
    assert 'content="/admin-react/api/v1/"' in body


@pytest.mark.django_db
def test_api_prefix_meta_honours_override(superuser_client: Client) -> None:
    """With `DJANGO_ADMIN_REACT["API_URL_PREFIX"]` set, the `dar-api-prefix`
    meta carries that value verbatim — the SPA will call that URL instead
    of the inline mount (#559)."""
    with override_settings(DJANGO_ADMIN_REACT={"API_URL_PREFIX": "/api/api/v1/"}):
        _reload_conf()
        try:
            response = superuser_client.get(ROOT_URL)
            assert response.status_code == 200
            body = response.content.decode("utf-8")
            assert 'name="dar-api-prefix"' in body
            assert 'content="/api/api/v1/"' in body
        finally:
            _reload_conf()


@pytest.mark.django_db
def test_api_prefix_meta_adds_trailing_slash_when_missing(superuser_client: Client) -> None:
    """Trailing slash invariant (#559): the SPA appends endpoint paths to
    the prefix, so the resolver always ensures one slash at the end even
    if the consumer's override omitted it."""
    with override_settings(DJANGO_ADMIN_REACT={"API_URL_PREFIX": "/custom-api/v1"}):
        _reload_conf()
        try:
            response = superuser_client.get(ROOT_URL)
            body = response.content.decode("utf-8")
            assert 'content="/custom-api/v1/"' in body
        finally:
            _reload_conf()


# --------------------------------------------------------------------------- #
# Legacy-admin escape hatch (#577) — opt-in banner pointer                    #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_legacy_admin_meta_absent_by_default(superuser_client: Client) -> None:
    """No `LEGACY_ADMIN_URL_PREFIX` setting → the `dar-legacy-admin-prefix`
    meta tag is **not** emitted, so the SPA renders no banner (#577).
    Existing consumers are unaffected; behaviour is identical to v1.0.x."""
    response = superuser_client.get(ROOT_URL)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="dar-legacy-admin-prefix"' not in body


@pytest.mark.django_db
def test_legacy_admin_meta_when_setting_enabled(superuser_client: Client) -> None:
    """With `LEGACY_ADMIN_URL_PREFIX` set, the `dar-legacy-admin-prefix`
    meta carries the normalised prefix so the SPA can render the
    escape-hatch banner (#577). Trailing slash invariant matches the
    `api_prefix` behaviour for parity."""
    with override_settings(DJANGO_ADMIN_REACT={"LEGACY_ADMIN_URL_PREFIX": "admin/"}):
        _reload_conf()
        try:
            response = superuser_client.get(ROOT_URL)
            assert response.status_code == 200
            body = response.content.decode("utf-8")
            assert 'name="dar-legacy-admin-prefix"' in body
            assert 'content="admin/"' in body
        finally:
            _reload_conf()


@pytest.mark.django_db
def test_legacy_admin_prefix_normalises_input(superuser_client: Client) -> None:
    """The resolver trims a leading slash and appends a trailing one so
    the SPA can always do `<origin>/<prefix><tail>` cleanly (#577)."""
    with override_settings(DJANGO_ADMIN_REACT={"LEGACY_ADMIN_URL_PREFIX": "/old-admin"}):
        _reload_conf()
        try:
            response = superuser_client.get(ROOT_URL)
            body = response.content.decode("utf-8")
            assert 'content="old-admin/"' in body
        finally:
            _reload_conf()


@pytest.mark.django_db
def test_legacy_admin_meta_absent_for_empty_string(superuser_client: Client) -> None:
    """An empty / whitespace-only override is treated like ``None`` —
    no meta emitted, no banner (#577). Defensive normalisation so a
    consumer doesn't accidentally render a banner to the site root."""
    with override_settings(DJANGO_ADMIN_REACT={"LEGACY_ADMIN_URL_PREFIX": "   "}):
        _reload_conf()
        try:
            response = superuser_client.get(ROOT_URL)
            body = response.content.decode("utf-8")
            assert 'name="dar-legacy-admin-prefix"' not in body
        finally:
            _reload_conf()


# --------------------------------------------------------------------------- #
# Reverse escape-hatch strip on the legacy admin (#584)                       #
# --------------------------------------------------------------------------- #
def _render_experience_strip(path: str, settings_overrides: dict[str, Any]) -> str:
    """Render the inclusion-tag inline against a synthetic request.

    Mirrors the way Django's admin templates render: a context dict that
    includes ``request``. Returns the rendered HTML (or "" when the tag
    short-circuits).
    """
    from django.template import Context
    from django.template import Template
    from django.test import RequestFactory

    with override_settings(DJANGO_ADMIN_REACT=settings_overrides):
        _reload_conf()
        try:
            req = RequestFactory().get(path)
            tpl = Template("{% load experience_toggle %}{% experience_toggle_strip %}")
            rendered = tpl.render(Context({"request": req}))
            return rendered.strip()
        finally:
            _reload_conf()


def test_reverse_strip_renders_nothing_when_both_prefixes_unset() -> None:
    """No prefixes configured → no DOM, no extra work (#584). Existing
    consumers who haven't opted into the escape hatch see no change to
    the legacy admin chrome."""
    out = _render_experience_strip("/admin/auth/user/", {})
    assert out == ""


def test_reverse_strip_renders_nothing_when_only_legacy_set() -> None:
    """Only `LEGACY_ADMIN_URL_PREFIX` (the SPA-side direction) → the
    reverse strip is intentionally off. We do NOT guess the consumer's
    SPA mount; the strip only renders when both prefixes agree (#584)."""
    out = _render_experience_strip(
        "/admin/auth/user/",
        {"LEGACY_ADMIN_URL_PREFIX": "admin/"},
    )
    assert out == ""


def test_reverse_strip_renders_link_under_react_mount() -> None:
    """Both prefixes set + request on the legacy admin → reverse strip
    points at the same path under the React mount (#584). The strip is
    the legacy mirror of the SPA-side banner."""
    out = _render_experience_strip(
        "/admin/auth/user/",
        {
            "LEGACY_ADMIN_URL_PREFIX": "admin/",
            "REACT_ADMIN_URL_PREFIX": "admin2/",
        },
    )
    assert 'href="/admin2/auth/user/"' in out
    assert "Open this page in /admin2/" in out


def test_reverse_strip_preserves_query_string() -> None:
    """The strip carries `request.GET` to the React side verbatim so a
    user on a filtered legacy changelist lands on the matching filtered
    React list (#584, mirror of #582 on the SPA side)."""
    out = _render_experience_strip(
        "/admin/auth/user/?ordering=id&status=active",
        {
            "LEGACY_ADMIN_URL_PREFIX": "admin/",
            "REACT_ADMIN_URL_PREFIX": "admin2/",
        },
    )
    # `&` is HTML-escaped to `&amp;` in attributes by Django's
    # auto-escape; the rendered URL is still correct.
    assert 'href="/admin2/auth/user/?ordering=id&amp;status=active"' in out


def test_reverse_strip_short_circuits_off_legacy_mount() -> None:
    """Defensive — the template override could in principle reach pages
    outside the legacy mount (e.g. if a consumer reuses
    `admin/base_site.html` from a non-admin app). The strip checks the
    current path matches the legacy prefix before rendering (#584)."""
    out = _render_experience_strip(
        "/some-other-app/page/",
        {
            "LEGACY_ADMIN_URL_PREFIX": "admin/",
            "REACT_ADMIN_URL_PREFIX": "admin2/",
        },
    )
    assert out == ""


def test_reverse_strip_template_has_no_leaking_hash_comments() -> None:
    """Regression for #596: a multi-line `{# ... #}` comment in the
    strip template leaked the `{#` / `#}` tokens onto the page as
    literal text (Django's `{# #}` is single-line only). The block-
    level `{% comment %}...{% endcomment %}` form must be used."""
    out = _render_experience_strip(
        "/admin/auth/user/",
        {
            "LEGACY_ADMIN_URL_PREFIX": "admin/",
            "REACT_ADMIN_URL_PREFIX": "admin2/",
        },
    )
    # The strip itself rendered (sanity check) AND no `{#` / `#}`
    # made it into the output as literal text.
    assert 'Open this page in /admin2/' in out
    assert "{#" not in out
    assert "#}" not in out


@pytest.mark.django_db
def test_reverse_strip_renders_above_admin_header_not_in_content(
    superuser_client: Client,
) -> None:
    """Regression for #595: the strip used to be injected inside
    `{% block content %}`, which Django's `change_list.html`,
    `change_form.html`, `index.html`, and `login.html` all override
    WITHOUT `{{ block.super }}` — silently discarding the strip on
    almost every page a user actually visits. Moved into
    `{% block header %}` (defined once in `admin/base.html`, not
    overridden by those templates), which renders the strip
    consistently across the whole admin surface."""
    with override_settings(
        DJANGO_ADMIN_REACT={
            "LEGACY_ADMIN_URL_PREFIX": "admin/",
            "REACT_ADMIN_URL_PREFIX": "admin2/",
        },
    ):
        _reload_conf()
        try:
            # Hit the legacy admin index — a page whose Django template
            # overrides `{% block content %}` without super (#595 repro).
            # In the test_project the legacy admin mounts at `/admin/`.
            response = superuser_client.get("/admin/")
            body = response.content.decode("utf-8")
            # Strip rendered:
            assert 'aria-label="Experience toggle"' in body
            # Strip is above the admin header markup (`<div id="header">`
            # in Django's `admin/base.html`), confirming it's in the
            # `header` block, not the `content` block.
            strip_idx = body.index('aria-label="Experience toggle"')
            header_idx = body.index('id="header"')
            assert strip_idx < header_idx, (
                "Strip must render above #header, not inside content"
            )
        finally:
            _reload_conf()


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
def test_brand_derives_header_and_title_from_admin_site(superuser_client: Client) -> None:
    """When `BRAND_TITLE` is unset, the SPA shell derives both brand
    strings from the AdminSite, mirroring Django admin: `site_header` is
    the sidebar header (the `dar-brand-title` meta) and `site_title` is
    the browser-tab `<title>` (#281). Consumers who already customised
    their AdminSite for the legacy admin need no extra setting.
    """
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        original_header = default_admin_site.site_header
        original_title = default_admin_site.site_title
        default_admin_site.site_header = "Operations Console"
        default_admin_site.site_title = "Ops"
        try:
            response = superuser_client.get(ROOT_URL)
            html = response.content.decode("utf-8")
            # Sidebar header ← site_header.
            assert 'name="dar-brand-title" content="Operations Console"' in html
            # Browser-tab <title> ← site_title (Django's tab-title source).
            assert "<title>Ops</title>" in html
        finally:
            default_admin_site.site_header = original_header
            default_admin_site.site_title = original_title


@pytest.mark.django_db
def test_tab_title_falls_back_to_site_header_when_no_site_title(superuser_client: Client) -> None:
    """If the AdminSite has no `site_title`, the tab `<title>` falls back
    to `site_header` (then the package name) — never blank (#281)."""
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        original_header = default_admin_site.site_header
        original_title = default_admin_site.site_title
        default_admin_site.site_header = "Operations Console"
        default_admin_site.site_title = ""  # falsy → fall through to header
        try:
            html = superuser_client.get(ROOT_URL).content.decode("utf-8")
            assert "<title>Operations Console</title>" in html
        finally:
            default_admin_site.site_header = original_header
            default_admin_site.site_title = original_title


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
def test_primary_color_falls_back_to_admin_site_attr(superuser_client: Client) -> None:
    """When `PRIMARY_COLOR` is unset, the SPA reads `site_primary_color`
    off the AdminSite — mirrors `site_header` / `site_logo` so a consumer
    with a custom AdminSite can brand from one place (#631)."""
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        original = getattr(default_admin_site, "site_primary_color", None)
        default_admin_site.site_primary_color = "#10b981"  # emerald
        try:
            html = superuser_client.get(ROOT_URL).content.decode("utf-8")
            assert "--dar-primary: #10b981;" in html
        finally:
            if original is None:
                del default_admin_site.site_primary_color
            else:
                default_admin_site.site_primary_color = original


@pytest.mark.django_db
def test_primary_color_setting_wins_over_admin_site_attr(superuser_client: Client) -> None:
    """Explicit `PRIMARY_COLOR` setting overrides `site_primary_color` —
    the setting is the per-deployment override, the attr is the
    structural default. Same precedence as `BRAND_TITLE` (#631)."""
    with override_settings(DJANGO_ADMIN_REACT={"PRIMARY_COLOR": "#ff8800"}):
        _reload_conf()
        original = getattr(default_admin_site, "site_primary_color", None)
        default_admin_site.site_primary_color = "#10b981"
        try:
            html = superuser_client.get(ROOT_URL).content.decode("utf-8")
            assert "--dar-primary: #ff8800;" in html
            assert "#10b981" not in html
        finally:
            if original is None:
                del default_admin_site.site_primary_color
            else:
                default_admin_site.site_primary_color = original


@pytest.mark.django_db
def test_primary_color_admin_site_non_hex_is_rejected(superuser_client: Client) -> None:
    """A non-hex `site_primary_color` on the AdminSite still can't inject
    CSS — same regex gate as `PRIMARY_COLOR`. Falls through to the
    default (#437 / #631)."""
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        original = getattr(default_admin_site, "site_primary_color", None)
        default_admin_site.site_primary_color = "red; } body { display: none } :root {"
        try:
            html = superuser_client.get(ROOT_URL).content.decode("utf-8")
            assert "display: none" not in html
            assert "--dar-primary: #2563eb;" in html
        finally:
            if original is None:
                del default_admin_site.site_primary_color
            else:
                default_admin_site.site_primary_color = original


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


@pytest.mark.django_db
def test_brand_logo_falls_back_to_admin_site_logo(superuser_client: Client) -> None:
    """When `BRAND_LOGO_URL` is unset, a `site_logo` attribute on the
    AdminSite is used — so a consumer can set the logo as a constant on
    their admin site, no separate setting (#281)."""
    with override_settings(DJANGO_ADMIN_REACT={}):
        _reload_conf()
        default_admin_site.site_logo = "/static/acme/site-logo.svg"
        try:
            html = superuser_client.get(ROOT_URL).content.decode("utf-8")
            assert 'name="dar-brand-logo" content="/static/acme/site-logo.svg"' in html
            assert 'rel="icon" href="/static/acme/site-logo.svg"' in html
        finally:
            del default_admin_site.site_logo


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
def test_react_login_off_anon_redirected(anon_client: Client) -> None:
    """Opt-out (`REACT_LOGIN=False`): anonymous users are redirected to
    the legacy login page with a `?next=` round-trip back to the SPA.
    Preserved as the escape hatch for consumers who don't want the
    React-rendered login (the default is `True` since 2026-05-28)."""
    with override_settings(DJANGO_ADMIN_REACT={"REACT_LOGIN": False}):
        _reload_conf()
        try:
            response = anon_client.get(ROOT_URL)
            assert response.status_code == 302
            location = response["Location"]
            assert "next=" in location
            query = parse_qs(urlsplit(location).query)
            assert query["next"][0].startswith(ROOT_URL)
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
