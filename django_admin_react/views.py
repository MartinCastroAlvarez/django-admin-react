"""SPA entry point view.

The SPA itself is a single ``index.html`` that ships with the package
under ``django_admin_react/templates/admin_react/index.html`` and a
bundle under ``django_admin_react/static/admin_react/``.

The view's only job is to:

1. Enforce the same authentication gate as the rest of the package
   (active + staff, or whatever ``AdminSite.has_permission`` says).
2. Render ``index.html`` with the resolved mount point so the SPA can
   construct API URLs without hardcoding.

Implementation lands in PR #6. This stub is enough for ``urls.py`` to
import cleanly and for the package to install.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.views.generic import View


class SpaIndexView(View):
    """Serves the built React SPA. Stubbed; implementation in PR #6."""

    def get(self, request, *args, **kwargs) -> HttpResponse:  # noqa: ARG002
        # Real implementation will:
        #   - Enforce staff auth (or AdminSite.has_permission).
        #   - Render templates/admin_react/index.html with the mount
        #     point and CSRF cookie set.
        # See docs/api-contract.md and ARCHITECTURE.md §4.5.
        raise NotImplementedError("SpaIndexView lands in PR #6")
