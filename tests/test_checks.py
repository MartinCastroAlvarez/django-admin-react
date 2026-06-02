"""System-check tests (#667).

Exercise every branch of ``django_admin_react.checks`` — the happy path
(no findings with the test project's correct config) and each failure
mode via ``override_settings`` / monkeypatching, asserting the right
check ID and that the message carries an actionable hint.
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from django_admin_react import checks as dar_checks


def _ids(findings: list) -> set[str]:
    return {f.id for f in findings}


def test_all_checks_pass_with_the_test_project_config() -> None:
    # The test project installs django_admin_rest_api, a valid ADMIN_SITE,
    # no unknown keys, the inline API mount, and a built manifest is present
    # in the package's static dir — so the only finding we tolerate is the
    # bundle-missing warning when running from a source checkout.
    findings = dar_checks.check_django_admin_react(None)
    blocking = [f for f in findings if f.id != dar_checks.ID_BUNDLE_MISSING]
    assert blocking == [], blocking


@override_settings(DJANGO_ADMIN_REACT={"NOPE_TYPO": 1})
def test_unknown_settings_key_is_an_error_with_hint() -> None:
    findings = dar_checks._check_settings_keys()
    assert _ids(findings) == {dar_checks.ID_UNKNOWN_SETTINGS}
    assert "NOPE_TYPO" in findings[0].msg
    assert findings[0].hint


def test_bad_admin_site_dotted_path_is_an_error() -> None:
    # ADMIN_SITE is read off the cached conf module; reload it under the
    # override so the bad value takes effect.
    import importlib

    from django_admin_react import conf as dar_conf

    with override_settings(DJANGO_ADMIN_REACT={"ADMIN_SITE": "does.not.exist.site"}):
        importlib.reload(dar_conf)
        try:
            findings = dar_checks._check_admin_site_imports()
        finally:
            # Restore the cached conf for the rest of the suite.
            importlib.reload(dar_conf)
    assert _ids(findings) == {dar_checks.ID_ADMIN_SITE_IMPORT}
    assert findings[0].hint


def test_api_prefix_set_emits_a_mount_warning() -> None:
    import importlib

    from django_admin_react import conf as dar_conf

    with override_settings(DJANGO_ADMIN_REACT={"API_URL_PREFIX": "/api/api/v1/"}):
        importlib.reload(dar_conf)
        try:
            findings = dar_checks._check_api_prefix_coherence()
        finally:
            importlib.reload(dar_conf)
    assert _ids(findings) == {dar_checks.ID_API_PREFIX_MOUNT}
    assert "/api/api/v1/" in findings[0].msg
    assert findings[0].hint


def test_api_prefix_unset_emits_no_warning() -> None:
    # Default test config leaves API_URL_PREFIX unset → inline mount → quiet.
    assert dar_checks._check_api_prefix_coherence() == []


def test_rest_api_missing_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from django.apps import apps as django_apps

    real_is_installed = django_apps.is_installed

    def fake_is_installed(label: str) -> bool:
        if label == "django_admin_rest_api":
            return False
        return real_is_installed(label)

    monkeypatch.setattr(django_apps, "is_installed", fake_is_installed)
    findings = dar_checks._check_rest_api_installed()
    assert _ids(findings) == {dar_checks.ID_REST_API_MISSING}
    assert "INSTALLED_APPS" in findings[0].hint


def test_bundle_missing_is_a_warning(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from django_admin_react import views

    # Point the manifest path at a file that doesn't exist.
    monkeypatch.setattr(views, "_MANIFEST_PATH", tmp_path / "missing-manifest.json")
    findings = dar_checks._check_bundle_built()
    assert _ids(findings) == {dar_checks.ID_BUNDLE_MISSING}
    assert findings[0].hint


def test_bundle_present_emits_no_warning(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from django_admin_react import views

    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(views, "_MANIFEST_PATH", manifest)
    assert dar_checks._check_bundle_built() == []


def test_check_is_registered_with_django() -> None:
    from django.core.checks import registry

    registered = {c for c in registry.registry.get_checks()}
    assert dar_checks.check_django_admin_react in registered
