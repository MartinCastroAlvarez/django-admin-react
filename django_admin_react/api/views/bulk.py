"""``PATCH /api/v1/<app>/<model>/bulk/`` — bulk PATCH endpoint.

Wire contract: ``docs/api-contract.md`` §5.5.

Powers ``list_editable`` and bulk-edit flows (Issue #61). The SPA
sends ``{updates: [{pk, fields: {...}}, ...]}`` and the package
runs each update through ``ModelAdmin.get_form()`` + ``save_model``
the same way the single-row PATCH does. Per-row errors are returned
in a uniform envelope so the SPA can show validation errors next to
the row that failed without losing the rest of the batch.

Hard rules (`SECURITY.md` §3):

- Rule 5:  ``has_change_permission(request, obj)`` per-row gate.
- Rule 6:  Writes go through ``ModelAdmin.get_form()`` then
           ``save_model(..., change=True)`` (B-3). Same form, same
           validation, same signals as the single-row PATCH.
- Rule 10: Each row's queryset starts at
           ``ModelAdmin.get_queryset(request)`` — never bypasses the
           admin's row-level filtering.
- Rule 12: ``readonly`` / ``exclude`` keys in any row payload → that
           row's error envelope cites the bad key. Other rows still
           apply.

Atomicity: a single ``transaction.atomic()`` wraps the whole batch.
If *any* row fails ``form.is_valid()`` or its per-row permission
check, the whole transaction rolls back and the response surfaces
the per-row errors. This matches the user's expected "all-or-nothing"
posture for a single Save click on a list_editable view.
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
from django_admin_react.api.writes import bad_request
from django_admin_react.api.writes import form_errors_to_envelope
from django_admin_react.api.writes import load_object_or_none
from django_admin_react.api.writes import log_change
from django_admin_react.api.writes import merged_initial_for_update
from django_admin_react.api.writes import not_found_response
from django_admin_react.api.writes import parse_json_body
from django_admin_react.api.writes import readonly_or_excluded_names
from django_admin_react.api.writes import reject_forbidden_keys
from django_admin_react.api.writes import writable_field_names

# Cap batch size: a single keystroke from a SPA worker should not be
# able to materialise 10k forms. 200 matches the package-wide
# ``MAX_PAGE_SIZE`` default so a "save the whole page" workflow fits
# in one batch.
_BULK_MAX_UPDATES = 200


class BulkUpdateView(View):
    """``PATCH /api/v1/<app>/<model>/bulk/``."""

    http_method_names = ["patch"]

    def patch(
        self,
        request: HttpRequest,
        app_label: str,
        model_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)

        resolved = resolve_model(admin_site, request, app_label, model_name)
        if resolved is None:
            return not_found_response()
        model, model_admin = resolved

        parsed = parse_json_body(request)
        if isinstance(parsed, HttpResponse):
            return parsed
        body: dict[str, Any] = parsed

        updates = body.get("updates")
        if not isinstance(updates, list) or not updates:
            return bad_request("`updates` must be a non-empty list.")
        if len(updates) > _BULK_MAX_UPDATES:
            return bad_request(f"`updates` exceeds the bulk cap of {_BULK_MAX_UPDATES}.")

        results: list[dict[str, Any]] = []
        accepted = 0
        rejected = 0

        # The atomic wraps the whole batch — any row that fails rolls
        # the entire transaction back. Per-row errors are still
        # collected and surfaced so the SPA can highlight the failing
        # rows; the SPA decides whether to retry the batch with the
        # failures dropped.
        with transaction.atomic():
            sid = transaction.savepoint()
            for entry in updates:
                row_result = _apply_one(model, model_admin, request, entry)
                results.append(row_result)
                if row_result.get("ok"):
                    accepted += 1
                else:
                    rejected += 1
            if rejected > 0:
                transaction.savepoint_rollback(sid)
                # Rebuild the result envelope so the caller knows the
                # accepted rows were rolled back too.
                results = [
                    {**r, "ok": False, "rolled_back": True} if r.get("ok") else r for r in results
                ]
                accepted = 0
                rejected = len(updates)
            else:
                transaction.savepoint_commit(sid)

        response = JsonResponse(
            {
                "results": results,
                "summary": {"accepted": accepted, "rejected": rejected},
            },
            status=200,
        )
        response["Cache-Control"] = "no-store"
        return response


def _apply_one(
    model: type,
    model_admin: Any,
    request: HttpRequest,
    entry: Any,
) -> dict[str, Any]:
    """Apply one update entry; return the per-row result envelope.

    Returns either ``{pk, ok: True}`` or ``{pk, ok: False, error:
    {code, message, fields?}}``. Never raises — every error path
    becomes a structured envelope so the caller's atomic wrapper can
    inspect ``ok`` to decide whether to roll back.
    """
    if not isinstance(entry, dict):
        return {
            "pk": None,
            "ok": False,
            "error": {"code": "bad_request", "message": "Entry must be an object."},
        }
    pk = entry.get("pk")
    fields = entry.get("fields")
    if pk is None:
        return {
            "pk": None,
            "ok": False,
            "error": {"code": "bad_request", "message": "`pk` is required."},
        }
    if not isinstance(fields, dict) or not fields:
        return {
            "pk": pk,
            "ok": False,
            "error": {"code": "bad_request", "message": "`fields` must be a non-empty object."},
        }

    obj = load_object_or_none(model, model_admin, request, pk)
    if obj is None:
        return {"pk": pk, "ok": False, "error": {"code": "not_found", "message": "Not found."}}

    if not model_admin.has_change_permission(request, obj):
        return {
            "pk": pk,
            "ok": False,
            "error": {"code": "forbidden", "message": "You do not have permission."},
        }

    writable = writable_field_names(model, model_admin, request, obj)
    forbidden = readonly_or_excluded_names(model_admin, request, obj)
    rejection = reject_forbidden_keys(fields, writable, forbidden)
    if rejection is not None:
        # Rejection body shape is already the wire format; unwrap it
        # so per-row error matches the rest of the envelope.
        body = rejection.content.decode("utf-8")
        import json as _json

        return {"pk": pk, "ok": False, "error": _json.loads(body)["error"]}

    form = model_admin.get_form(request, obj=obj)(
        data=merged_initial_for_update(obj, writable, fields, model),
        files=None,
        instance=obj,
    )
    if not form.is_valid():
        return {
            "pk": pk,
            "ok": False,
            "error": {
                "code": "validation_failed",
                "message": "One or more fields are invalid.",
                "fields": form_errors_to_envelope(form),
            },
        }

    instance = form.save(commit=False)
    model_admin.save_model(request, instance, form, change=True)
    form.save_m2m()
    log_change(model_admin, request, instance, form)
    return {"pk": pk, "ok": True}
