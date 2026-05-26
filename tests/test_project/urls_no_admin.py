"""Test urlconf with the legacy Django admin **removed**.

Exercises the "consumer turned ``django.contrib.admin`` off" path: only
``django_admin_react`` is mounted, so there is no ``admin:login`` to
reverse and the package must fall back to its own ``login/`` page.
"""

from __future__ import annotations

from django.urls import include
from django.urls import path

urlpatterns = [
    path("admin-react/", include("django_admin_react.urls")),
]
