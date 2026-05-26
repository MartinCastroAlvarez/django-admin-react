"""URL patterns for the JSON API.

Mounted under the consumer's chosen prefix at ``api/v1/``. See
``django_admin_react/urls.py`` and ``docs/api-contract.md`` for the
overall path layout.

Each path serves multiple HTTP methods via a thin dispatch class so the
per-method implementation files stay focused. CSRF protection is the
consumer's middleware (`SECURITY.md` §3 rule 4); no view here is
``@csrf_exempt``.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.http import HttpResponse
from django.urls import path
from django.views.generic import View

from django_admin_react.api.views.create import CreateView
from django_admin_react.api.views.delete import DeleteView
from django_admin_react.api.views.detail import DetailView
from django_admin_react.api.views.list import ListView
from django_admin_react.api.views.registry import RegistryView
from django_admin_react.api.views.update import UpdateView

app_name = "api_v1"


class CollectionView(View):
    """Dispatch GET → list, POST → create for ``/<app>/<model>/``."""

    http_method_names = ["get", "post"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return ListView.as_view()(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return CreateView.as_view()(request, *args, **kwargs)


class InstanceView(View):
    """Dispatch GET / PATCH / DELETE for ``/<app>/<model>/<pk>/``."""

    http_method_names = ["get", "patch", "delete"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return DetailView.as_view()(request, *args, **kwargs)

    def patch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return UpdateView.as_view()(request, *args, **kwargs)

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return DeleteView.as_view()(request, *args, **kwargs)


urlpatterns: list = [
    path("registry/", RegistryView.as_view(), name="registry"),
    path(
        "<str:app_label>/<str:model_name>/",
        CollectionView.as_view(),
        name="collection",
    ),
    path(
        "<str:app_label>/<str:model_name>/<str:pk>/",
        InstanceView.as_view(),
        name="instance",
    ),
]
