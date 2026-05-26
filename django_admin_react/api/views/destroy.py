"""DELETE /api/v1/<app>/<model>/<pk>/ — delete endpoint.

Wire contract: ``docs/api-contract.md`` §5.3.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_view_permission(request, obj)`` per-object gate (to
           avoid revealing existence).
- Rule 7:  Calls ``ModelAdmin.delete_model(request, obj)`` — **never**
           ``obj.delete()`` directly (B-4).
- Rule 10: Queryset starts at ``ModelAdmin.get_queryset(request)`` —
           never ``Model.objects.all()`` (B-2).
- CSRF:    No ``@csrf_exempt`` — Django's middleware enforces.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model


class DestroyView(View):
    """``DELETE /api/v1/<app_label>/<model_name>/<pk>/``.

    Class name follows DRF's verb convention (``destroy``) to avoid
    overloading ``delete`` on the module surface; the HTTP method
    handler below must still be named ``delete`` per Django's CBV
    contract.
    """

    http_method_names = ["delete"]

    def delete(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response()

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return _not_found()
        model, model_admin = resolved

        try:
            obj = model_admin.get_queryset(request).get(pk=pk)
        except model.DoesNotExist:
            return _not_found()
        except (ValueError, TypeError):
            return _not_found()

        if not model_admin.has_delete_permission(request, obj):
            return forbidden_response()

        with transaction.atomic():
            model_admin.delete_model(request, obj)

        response = HttpResponse(status=204)
        response["Cache-Control"] = "no-store"
        return response


def _not_found() -> HttpResponse:
    response = JsonResponse(
        {"error": {"code": "not_found", "message": "Not found."}},
        status=404,
    )
    response["Cache-Control"] = "no-store"
    return response
