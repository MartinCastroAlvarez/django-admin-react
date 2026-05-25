"""URL patterns for the JSON API.

Mounted under the consumer's chosen prefix at ``api/v1/``. See
``django_admin_react/urls.py`` and ``docs/api-contract.md`` for the
overall path layout.

Implementation lands across PRs #3-#5. This is a stub so the parent
``urls.py`` can ``include()`` it cleanly.
"""

from __future__ import annotations

from django.urls import path

app_name = "api_v1"

urlpatterns: list = [
    # GET /api/v1/registry/                                   — PR #3
    # GET /api/v1/<app_label>/<model_name>/                   — PR #4
    # POST /api/v1/<app_label>/<model_name>/                  — PR #5
    # GET /api/v1/<app_label>/<model_name>/<pk>/              — PR #4
    # PATCH /api/v1/<app_label>/<model_name>/<pk>/            — PR #5
    # DELETE /api/v1/<app_label>/<model_name>/<pk>/           — PR #5
    # Routes are intentionally empty until each PR lands.
]
