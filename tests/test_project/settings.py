"""Minimal Django settings for the test suite.

This is **not** a configuration consumers should copy. It exists only so
``pytest-django`` can boot Django and the package's URL/admin wiring
during tests.
"""

from __future__ import annotations

import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "test-only-" + secrets.token_urlsafe(16)  # noqa: S105
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # **Minimal plug-and-play (#564 owner directive 2026-05-28):** only
    # `django_admin_react` is registered. `pip install django-admin-react`
    # transitively pulls in `django-admin-rest-api`; the URL include in
    # `django_admin_react.urls` mounts the API at `<mount>/api/v1/`, so
    # the API package does not need its own `INSTALLED_APPS` entry — the
    # endpoints resolve through `include("django_admin_rest_api.api.urls")`
    # without the AppConfig being registered (the API ships zero models +
    # zero signals, so the registration adds nothing the URL include needs).
    # Test-suite parity with the README's recommended snippet.
    "django_admin_react",
    # Test-only app with a FileField model retained for back-compat
    # (the package's own suite owns the upload tests now).
    "tests.test_project.uploads",
]

# Uploaded files land in a throwaway temp dir during tests — never the repo
# tree. ``FileField`` storage sanitises filenames (``get_valid_name`` /
# ``get_available_name``), which the upload tests rely on for path-traversal
# safety (#241).
import tempfile  # noqa: E402

MEDIA_ROOT = tempfile.mkdtemp(prefix="dar-test-media-")
MEDIA_URL = "/media/"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "tests.test_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
USE_TZ = True
TIME_ZONE = "UTC"

LOGIN_URL = "/admin/login/"
