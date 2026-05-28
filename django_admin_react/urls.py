"""Top-level URL configuration for django_admin_react.

This module is intended to be `include()`d by the consumer at any prefix:

    from django.urls import include, path
    urlpatterns = [
        path("admin-react/", include("django_admin_react.urls")),
    ]

The patterns below are split into:

1. **`api/v1/...`** — JSON endpoints exposed by the sibling package
   `django-admin-rest-api` (PyPI). **This repo implements no API of
   its own** — it is the React SPA super-layer over that package. The
   wire surface, permissions, serializer denylist, write enforcement
   and all per-endpoint behaviour live there.
2. **`login/` / `logout/`** — the package's own login (replaces the
   legacy admin login when the consumer turns `django.contrib.admin`
   off). Reuses Django's session auth; no parallel auth system.
3. **`web.manifest` / `sw.js`** — PWA surface.
4. **Everything else** under the mount point falls through to the SPA
   shell view, which serves `index.html` and lets React Router handle
   client-side routes.
"""

from __future__ import annotations

from django.urls import include
from django.urls import path
from django.urls import re_path

from django_admin_react import pwa
from django_admin_react import views

app_name = "django_admin_react"

urlpatterns: list = [
    # API endpoints — implemented by the sibling `django-admin-rest-api`
    # package, included here at the same `api/v1/` prefix the SPA already
    # expects. No URL namespace: the SPA builds these URLs from the wire
    # contract, not via Django's `reverse()`, so a namespace would be
    # dead weight.
    path("api/v1/", include("django_admin_rest_api.api.urls")),
    # The package's own login / logout. These let the package replace
    # the legacy admin's login when the consumer turns
    # ``django.contrib.admin`` off — ``SpaIndexView`` falls back to
    # ``django_admin_react:login`` when no admin login is reachable.
    # Both reuse Django's session auth (``LoginView`` / ``LogoutView``);
    # no parallel auth system. Declared before the SPA catch-all so the
    # literal ``login/`` / ``logout/`` segments aren't swallowed.
    path("login/", views.DarLoginView.as_view(), name="login"),
    path("logout/", views.DarLogoutView.as_view(), name="logout"),
    # PWA surface (Issue #86). Literal segments, declared before the
    # SPA catch-all so they aren't swallowed by it. The manifest is
    # intentionally anonymous (the install prompt fires pre-login); the
    # SW is served with a Service-Worker-Allowed header scoped to the
    # mount. See ``django_admin_react/pwa.py``.
    path("web.manifest", pwa.ManifestView.as_view(), name="pwa_manifest"),
    path("sw.js", pwa.ServiceWorkerView.as_view(), name="pwa_service_worker"),
    # SPA fallback. The catch-all is intentionally last so any
    # server-rendered route above takes precedence.
    re_path(r"^.*$", views.SpaIndexView.as_view(), name="spa_index"),
]
