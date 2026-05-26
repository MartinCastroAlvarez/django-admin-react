"""Tests for the SPA index view at the package's mount URL.

The view serves the React shell HTML to staff. It is the only
non-API view in the package, and it enforces the same auth gate
the API uses (rule 1 in ``SECURITY.md`` §3).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
from django.test import Client

import django_admin_react.views as views_module
from django_admin_react import views

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
    # parameter so the user lands back here after login.
    assert "next=" in response["Location"]
    assert ROOT_URL in response["Location"]


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
