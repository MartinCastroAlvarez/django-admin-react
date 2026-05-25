"""URL configuration for the test project.

The package is mounted at ``/admin-react/`` so tests can exercise the
configurable mount point (`ARCHITECTURE.md` §4.5). The legacy admin is
mounted at ``/admin/`` so authentication and CSRF behave as a consumer
would experience them.
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import include
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin-react/", include("django_admin_react.urls")),
]
