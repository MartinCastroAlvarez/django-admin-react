"""Permission helpers.

The package's default permission gate is:

    user.is_authenticated and user.is_active and user.is_staff
    and admin_site.has_permission(request)

Per-operation gates always go through the relevant
``ModelAdmin.has_*_permission(request, obj=None)`` method.

See ``SECURITY.md`` §3 (rules 1 and 12) for the contract this enforces.
"""

from __future__ import annotations

from typing import Final

from django.contrib.admin.sites import AdminSite
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse

from django_admin_react.api.registry import get_admin_site


def _user_is_active_staff(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    return bool(
        user is not None
        and user.is_authenticated
        and getattr(user, "is_active", False)
        and getattr(user, "is_staff", False)
    )


def is_admin_user(request: HttpRequest, admin_site: AdminSite | None = None) -> bool:
    """Return True iff the request may access the package's API.

    The package's default policy is staff-only (rule 1 in ``SECURITY.md``
    §3). ``AdminSite.has_permission`` is the consumer's escape hatch: if
    a consumer's custom site allows non-staff users to access the admin,
    this package follows that decision (`ARCHITECTURE.md` §4.2).
    """
    if not _user_is_active_staff(request):
        return False
    site = admin_site if admin_site is not None else get_admin_site()
    return bool(site.has_permission(request))


_FORBIDDEN_BODY: Final[dict[str, dict[str, str]]] = {
    "error": {"code": "forbidden", "message": "You do not have permission."}
}


def forbidden_response() -> HttpResponse:
    """Return the package's canonical 403 envelope.

    The body never includes data identifying the resource (per ``SECURITY.md``
    §3 rule 12). For unauthenticated requests, callers may also want to
    redirect to ``settings.LOGIN_URL`` — that's a caller-level choice and
    not encoded here.
    """
    response = JsonResponse(_FORBIDDEN_BODY, status=403)
    # Discourage caching of a permission decision.
    response["Cache-Control"] = "no-store"
    return response
