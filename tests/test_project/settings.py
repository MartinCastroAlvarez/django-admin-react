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
    "django_admin_react",
    # Test-only app with a FileField model for the upload write path (#241).
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
