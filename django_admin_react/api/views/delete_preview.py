"""``GET /api/v1/<app>/<model>/<pk>/delete-preview/`` — cascade preview.

Wire contract: ``docs/api-contract.md`` §5.3 (delete preview sub-resource).

Django's HTML admin shows a confirmation interstitial before a delete:
what cascades, what's protected, what extra permissions are needed. The
SPA's Delete button should open the same preview before invoking the
DELETE endpoint — otherwise a single click can silently cascade-delete
related rows the operator never saw. Parity (#153).

Reuses ``django.contrib.admin.utils.get_deleted_objects`` — the exact
function the HTML admin's ``delete_view`` uses — so the cascade,
protected, and perms-needed sets match the legacy admin 1:1.

Hard rules (`SECURITY.md` §3):

- Rule 1:  Staff + ``AdminSite.has_permission`` gate.
- Rule 3:  Model resolved through ``admin.site._registry`` (B-7).
- Rule 5:  Per-object ``has_delete_permission`` gate.
- Rule 10: Object loaded through ``ModelAdmin.get_queryset(request)``.
- CSRF:    GET is safe; this endpoint never deletes — it only previews.
"""

from __future__ import annotations

from typing import Any

from django.contrib.admin.utils import get_deleted_objects
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.registry import resolve_model
from django_admin_react.api.serializers import label_for
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import not_found_response


class DeletePreviewView(View):
    """``GET /api/v1/<app_label>/<model_name>/<pk>/delete-preview/``."""

    http_method_names = ["get"]

    def get(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        pk: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Return the cascade / protected / perms-needed preview.

        Gates mirror the DELETE endpoint exactly (``has_delete_permission``)
        so the preview never reveals cascade structure for an object the
        user couldn't delete anyway. 404 (no oracle) on missing /
        unviewable; 403 on lacking delete permission.

        This endpoint **never** mutates — it only computes the preview.
        The actual delete still goes through ``DELETE`` →
        ``ModelAdmin.delete_model`` (rule 7).
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

        # Django's own delete_view machinery. Returns:
        #   deletable  — nested list of str reprs (display tree)
        #   model_count— {verbose_name_plural: count}
        #   perms_needed — set of verbose_names the user can't delete
        #   protected  — list of str reprs blocking the delete (PROTECT)
        _deletable, model_count, perms_needed, protected = get_deleted_objects(
            [obj], request, admin_site
        )

        body = {
            "object": {"pk": obj.pk, "label": label_for(obj)},
            "cascade": [
                {"model": str(model_label), "count": int(count)}
                for model_label, count in model_count.items()
            ],
            "protected": [str(p) for p in protected],
            "perms_needed": sorted(str(p) for p in perms_needed),
            # The delete proceeds only when nothing is PROTECT-blocked and
            # the user holds delete permission on every cascading model.
            "can_delete": not protected and not perms_needed,
        }
        response = JsonResponse(body, status=200)
        response["Cache-Control"] = "no-store"
        return response
