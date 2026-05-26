"""URL patterns for the JSON API.

Mounted under the consumer's chosen prefix at ``api/v1/``. See
``django_admin_react/urls.py`` and ``docs/api-contract.md`` for the
overall path layout.
"""

from __future__ import annotations

from django.urls import path

from django_admin_react.api.views.detail import DetailView
from django_admin_react.api.views.list import ListView
from django_admin_react.api.views.registry import RegistryView

app_name = "api_v1"

urlpatterns: list = [
    path("registry/", RegistryView.as_view(), name="registry"),
    path(
        "<str:app_label>/<str:model_name>/",
        ListView.as_view(),
        name="list",
    ),
    path(
        "<str:app_label>/<str:model_name>/<str:pk>/",
        DetailView.as_view(),
        name="detail",
    ),
    # POST /<app>/<model>/                    — PR #5
    # PATCH /<app>/<model>/<pk>/              — PR #5
    # DELETE /<app>/<model>/<pk>/             — PR #5
]
