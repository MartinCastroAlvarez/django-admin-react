"""``DELETE /api/v1/<app>/<model>/<pk>/`` — destroy endpoint.

Wire contract: ``docs/api-contract.md`` §5.3.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  ``has_delete_permission(request, obj)`` per-object gate.
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
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import not_found_response


class DestroyView(View):
    """``DELETE /api/v1/<app_label>/<model_name>/<pk>/``.

    The class name follows DRF's verb convention (``destroy``) to
    avoid overloading the module surface — ``del`` is a Python
    keyword and ``.delete()`` is a Django QuerySet/Model method, so
    a *class* named ``DeleteView`` muddies imports. The HTTP-method
    handler must still be named ``delete`` per Django's CBV
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
        """Delete an instance (contract §5.3).

        Gates: ``is_admin_user`` → ``resolve_model`` →
        ``load_object_or_none`` (the admin's queryset is the only
        lookup path — rule 10 / B-2) → ``has_delete_permission(request,
        obj)`` per-object gate.

        The actual delete goes through ``ModelAdmin.delete_model(request,
        obj)`` — **never** ``obj.delete()`` — so any admin-side
        cascade / hook logic is honored (rule 7 / B-4). Wrapped in
        ``transaction.atomic()``. Returns a 204 (No Content) with
        ``Cache-Control: no-store``.
        """
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        obj = load_object_or_none(model, model_admin, request, pk)
        if obj is None:
            return not_found_response()

        if not model_admin.has_delete_permission(request, obj):
            return forbidden_response(request)

        with transaction.atomic():
            model_admin.delete_model(request, obj)

        response = HttpResponse(status=204)
        response["Cache-Control"] = "no-store"
        return response
