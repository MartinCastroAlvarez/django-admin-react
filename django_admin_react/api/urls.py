"""URL patterns for the JSON API.

Mounted under the consumer's chosen prefix at ``api/v1/``. See
``django_admin_react/urls.py`` and ``docs/api-contract.md`` for the
overall path layout.

Implementation lands across PRs #3-#5. This is a stub so the parent
``urls.py`` can ``include()`` it cleanly.
"""

from __future__ import annotations

from django.urls import path

from django_admin_react.api.views.registry import RegistryView

app_name = "api_v1"

urlpatterns: list = [
    path("registry/", RegistryView.as_view(), name="registry"),
    # GET /api/v1/<app_label>/<model_name>/                   — PR #4
    # POST /api/v1/<app_label>/<model_name>/                  — PR #5
    # GET /api/v1/<app_label>/<model_name>/<pk>/              — PR #4
    # PATCH /api/v1/<app_label>/<model_name>/<pk>/            — PR #5
    # DELETE /api/v1/<app_label>/<model_name>/<pk>/           — PR #5
]
