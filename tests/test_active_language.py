"""Tests for ``_resolve_active_language`` (#630).

The SPA reads ``<meta name="dar-language">`` at boot to pick its
chrome message catalog. The server resolves the language code from
Django's translation machinery: when ``LocaleMiddleware`` is in the
stack, it activates the request's language before the view runs and
``translation.get_language()`` returns that code; without the
middleware, the call collapses to ``settings.LANGUAGE_CODE``.

These tests cover both modes — the package shouldn't enforce
``LocaleMiddleware`` but it MUST work with or without it.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.test import override_settings
from django.utils import translation


@pytest.fixture
def staff_client(db):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_superuser(
        username="i18n-su",
        email="i18n@example.com",
        password="x",  # noqa: S106
    )
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
def test_dar_language_meta_is_emitted(staff_client: Client) -> None:
    """The shell template MUST emit ``<meta name="dar-language">`` so the
    SPA can hydrate its catalog at boot. The exact value depends on the
    request's active locale; the tag's presence is the load-bearing
    invariant (#630)."""
    response = staff_client.get("/admin-react/")
    html = response.content.decode("utf-8")
    assert 'name="dar-language"' in html, html


@pytest.mark.django_db
def test_active_language_defaults_to_language_code_when_no_localemiddleware(
    staff_client: Client,
) -> None:
    """Without ``LocaleMiddleware`` in MIDDLEWARE, ``translation
    .get_language()`` returns ``settings.LANGUAGE_CODE`` — the SPA's
    fallback locale. The test_project's MIDDLEWARE list intentionally
    omits ``LocaleMiddleware`` (matches Django's ``startproject``
    template), so this is the default-deploy case (#630)."""
    with override_settings(LANGUAGE_CODE="en-us"):
        translation.deactivate_all()
        response = staff_client.get("/admin-react/")
        html = response.content.decode("utf-8")
        # Django's ``get_language()`` may return the stem (``en``) or
        # the full code (``en-us``) depending on locale activation
        # state — accept either; the load-bearing invariant is that
        # the meta tag is populated with a reasonable code.
        assert (
            'name="dar-language" content="en-us"' in html
            or 'name="dar-language" content="en"' in html
        )


@pytest.mark.django_db
def test_active_language_follows_activate(staff_client: Client) -> None:
    """When something HAS activated a locale (LocaleMiddleware in real
    deployments, or an explicit ``translation.activate`` for the test),
    ``_resolve_active_language`` follows it. Mirrors what a Spanish-
    primary shop sees: the SPA gets ``es`` in the meta, hydrates the
    Spanish catalog, renders translated chrome (#630)."""
    with override_settings(LANGUAGE_CODE="en-us", USE_I18N=True):
        translation.activate("es")
        try:
            response = staff_client.get("/admin-react/")
            html = response.content.decode("utf-8")
            assert 'name="dar-language" content="es"' in html
        finally:
            translation.deactivate_all()
