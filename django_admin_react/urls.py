"""Top-level URL configuration for django_admin_react.

This module is intended to be `include()`d by the consumer at any
prefix:

    from django.urls import include, path
    urlpatterns = [
        path("admin-react/", include("django_admin_react.urls")),
    ]

The patterns below are split into two groups:

1. `api/v1/...` — JSON endpoints documented in `docs/api-contract.md`.
2. Everything else under the mount point falls through to the SPA
   shell view, which serves `index.html` and lets React Router handle
   client-side routes.

Implementation lands in PRs #3-#5 (backend) and #6 (frontend index).
"""

from __future__ import annotations

from django.urls import include
from django.urls import path
from django.urls import re_path

from django_admin_react import views

app_name = "django_admin_react"

urlpatterns: list = [
    # API endpoints. No URL namespace: the SPA builds these URLs from
    # the wire contract (see ``docs/api-contract.md``), not via Django's
    # ``reverse()``, so a namespace would be dead weight.
    path("api/v1/", include("django_admin_react.api.urls")),
    # The package's own login / logout. These let the package replace
    # the legacy admin's login when the consumer turns
    # ``django.contrib.admin`` off — ``SpaIndexView`` falls back to
    # ``django_admin_react:login`` when no admin login is reachable.
    # Both reuse Django's session auth (``LoginView`` / ``LogoutView``);
    # no parallel auth system. Declared before the SPA catch-all so the
    # literal ``login/`` / ``logout/`` segments aren't swallowed.
    path("login/", views.DarLoginView.as_view(), name="login"),
    path("logout/", views.DarLogoutView.as_view(), name="logout"),
    # SPA fallback. The catch-all is intentionally last so any
    # server-rendered route above takes precedence.
    re_path(r"^.*$", views.SpaIndexView.as_view(), name="spa_index"),
]
