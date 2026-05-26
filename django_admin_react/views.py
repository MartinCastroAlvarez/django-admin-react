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
        """Render the SPA shell (stub).

        Real implementation (tracked as a Security follow-up after
        PR #35) will:

        - Enforce staff auth via ``is_admin_user(request)``.
        - Render ``templates/admin_react/index.html`` with the
          resolved mount point so the SPA can construct API URLs
          without hardcoding.
        - Apply ``@method_decorator(ensure_csrf_cookie, name="dispatch")``
          so the SPA's first request always has a CSRF token (S-28).
        """
        raise NotImplementedError(
            "SpaIndexView implementation pending — tracked in "
            "docs/agents/security-expert/NEXT_STEPS.md."
        )
