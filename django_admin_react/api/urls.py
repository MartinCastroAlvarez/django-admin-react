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
from django.http import HttpResponseBase
from django.urls import path
from django.views.generic import View

from django_admin_react.api.panels import PanelView
from django_admin_react.api.views.actions import ActionView
from django_admin_react.api.views.auth import LoginView
from django_admin_react.api.views.auth import LogoutView
from django_admin_react.api.views.autocomplete import AutocompleteView
from django_admin_react.api.views.bulk import BulkUpdateView
from django_admin_react.api.views.create import CreateView
from django_admin_react.api.views.create_form import AddFormView
from django_admin_react.api.views.delete_preview import DeletePreviewView
from django_admin_react.api.views.destroy import DestroyView
from django_admin_react.api.views.detail import DetailView
from django_admin_react.api.views.history import HistoryView
from django_admin_react.api.views.list import ListView
from django_admin_react.api.views.password import SetPasswordView
from django_admin_react.api.views.registry import RegistryView
from django_admin_react.api.views.schema import SchemaView
from django_admin_react.api.views.update import UpdateView


class CollectionView(View):
    """Dispatch GET → list, POST → create for ``/<app>/<model>/``.

    The collection URL serves two HTTP verbs; rather than overloading
    a single view module, we dispatch to dedicated per-verb views so
    each verb's security gates and tests stay self-contained.
    """

    http_method_names = ["get", "post"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Forward GET to ``ListView`` (contract §3)."""
        return ListView.as_view()(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Forward POST to ``CreateView`` (contract §5.1)."""
        return CreateView.as_view()(request, *args, **kwargs)


class InstanceView(View):
    """Dispatch GET / PATCH / DELETE for ``/<app>/<model>/<pk>/``.

    Same pattern as :class:`CollectionView` — per-verb dispatch keeps
    the security gates and tests for read / change / delete cleanly
    separated.
    """

    http_method_names = ["get", "patch", "delete"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Forward GET to ``DetailView`` (contract §4)."""
        return DetailView.as_view()(request, *args, **kwargs)

    def patch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Forward PATCH to ``UpdateView`` (contract §5.2)."""
        return UpdateView.as_view()(request, *args, **kwargs)

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Forward DELETE to ``DestroyView`` (contract §5.3)."""
        return DestroyView.as_view()(request, *args, **kwargs)


urlpatterns: list = [
    path("registry/", RegistryView.as_view(), name="registry"),
    path("schema/", SchemaView.as_view(), name="schema"),
    # Auth endpoints (React-login feature). Single-segment literals, so
    # they cannot be shadowed by the two-segment ``<app>/<model>/``
    # pattern below. ``login`` / ``logout`` are also added to
    # ``RESERVED_APP_LABELS`` so a consumer app named ``login`` can't
    # collide. CSRF is enforced by middleware (no ``@csrf_exempt``).
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Autocomplete is more specific than the collection / instance
    # patterns below — it must be listed FIRST so the literal
    # ``/autocomplete/`` segment isn't swallowed as a ``<str:pk>``.
    path(
        "<str:app_label>/<str:model_name>/autocomplete/",
        AutocompleteView.as_view(),
        name="autocomplete",
    ),
    # Action endpoint must precede the instance pattern below for the
    # same reason — ``actions`` would otherwise be swallowed as a pk.
    path(
        "<str:app_label>/<str:model_name>/actions/<str:action_name>/",
        ActionView.as_view(),
        name="action",
    ),
    # Bulk PATCH endpoint — same ordering caveat (``bulk`` literal
    # before the ``<pk>`` pattern below).
    path(
        "<str:app_label>/<str:model_name>/bulk/",
        BulkUpdateView.as_view(),
        name="bulk_update",
    ),
    # Add-form schema — the create page's field descriptors for a NEW
    # object. Literal ``add`` must precede the ``<pk>`` instance route
    # below so it isn't swallowed as a pk.
    path(
        "<str:app_label>/<str:model_name>/add/",
        AddFormView.as_view(),
        name="add_form",
    ),
    path(
        "<str:app_label>/<str:model_name>/",
        CollectionView.as_view(),
        name="collection",
    ),
    # Panel endpoint (Issue #65) — opt-in via PanelEndpointsMixin on
    # the ModelAdmin. Must precede the instance pattern below so the
    # ``/panel/<name>/`` segment isn't swallowed.
    path(
        "<str:app_label>/<str:model_name>/<str:pk>/panel/<str:panel_name>/",
        PanelView.as_view(),
        name="panel",
    ),
    # History sub-resource (#155) — LogEntry timeline for one object.
    # Must precede the instance pattern so ``/history/`` isn't
    # swallowed as part of the ``<pk>`` route.
    path(
        "<str:app_label>/<str:model_name>/<str:pk>/history/",
        HistoryView.as_view(),
        name="history",
    ),
    # Delete-preview sub-resource (#153) — cascade / protected preview
    # before the destructive DELETE. Same ordering caveat as above.
    path(
        "<str:app_label>/<str:model_name>/<str:pk>/delete-preview/",
        DeletePreviewView.as_view(),
        name="delete_preview",
    ),
    # Password set/change sub-resource (#252) — UserAdmin parity. Literal
    # ``password`` segment must precede the ``<pk>`` instance route below.
    # 404s for any model whose admin has no password-change form.
    path(
        "<str:app_label>/<str:model_name>/<str:pk>/password/",
        SetPasswordView.as_view(),
        name="set_password",
    ),
    path(
        "<str:app_label>/<str:model_name>/<str:pk>/",
        InstanceView.as_view(),
        name="instance",
    ),
]
