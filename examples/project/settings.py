"""Demo Django project that hosts every `examples/*` app.

Intentionally minimal — this is **not** a production-ready settings
module. It exists so contributors and reviewers can run the example
apps end-to-end against `django-admin-react`.

Security-relevant notes:

- `SECRET_KEY` is generated on first run if `DJANGO_SECRET_KEY` is
  unset. It is never committed.
- `DEBUG` defaults to True for local dev; flip it via the
  `DJANGO_DEBUG` env var.
- `ALLOWED_HOSTS` is permissive in dev; tighten in any non-local
  deployment.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or "dev-only-" + secrets.token_urlsafe(32)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # The package under development. Importable as soon as the skeleton
    # PR (#2) lands; safe to keep here from the start because Django
    # tolerates apps without models.
    "django_admin_react",
    # Example apps the project demonstrates:
    "examples.fintech",
    "examples.library",
    "examples.blog",
    "examples.ecommerce",
    "examples.hr",
    # Custom-form fixture: a ModelAdmin with a request-driven custom view +
    # custom template, proving the legacy-iframe escape hatch (#659).
    "examples.jobs",
    # Many-actions fixture: a ModelAdmin with 12 batch + 2 detail-only
    # actions, pinning the detail-page toolbar wrapping behaviour (#672).
    "examples.many_actions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "examples.project.urls"

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

WSGI_APPLICATION = "examples.project.wsgi.application"
ASGI_APPLICATION = "examples.project.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Optional package-level config (every key is optional — defaults shown
# in `django_admin_react/conf.py` once that file lands in PR #2).
DJANGO_ADMIN_REACT = {
    "ADMIN_SITE": "django.contrib.admin.site",
    "DEFAULT_PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 200,
}

# Session / CSRF — make sure dev keeps both on (we never disable in
# production either).
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # React reads the token cookie.

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
