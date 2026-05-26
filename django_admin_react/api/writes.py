"""Shared helpers for the write endpoints (POST / PATCH / DELETE).

Wire contract: ``docs/api-contract.md`` §5 and §6.

Hard rules (`SECURITY.md` §3, `ACCEPTANCE.md` §3.1):

- Rule 6:  Writes go through ``ModelAdmin.get_form()`` — never
           ``setattr(obj, ...)`` directly (B-3).
- Rule 7:  Deletes go through ``ModelAdmin.delete_model()`` — never
           ``obj.delete()`` (B-4).
- Rule 12: ``readonly`` / ``exclude`` field names in the payload are a
           400 ``bad_request`` (S-31, B-3).
- Defense-in-depth: sensitive-name denylist is applied on top of the
  admin's own ``exclude`` so a misconfigured admin still cannot leak.
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.admin.options import ModelAdmin
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse

from django_admin_react.api.serializers import filter_sensitive
from django_admin_react.api.serializers import is_sensitive_field_name

_BAD_REQUEST_BODY: dict[str, Any] = {
    "error": {"code": "bad_request", "message": "Malformed request."}
}
_NOT_FOUND_BODY: dict[str, Any] = {"error": {"code": "not_found", "message": "Not found."}}


def bad_request(message: str = "Malformed request.") -> HttpResponse:
    """Return a uniform 400 envelope.

    The ``message`` is safe to surface to the client; never include
    request-derived strings here (per ``SECURITY.md`` §3 rule 12).
    """
    body = {"error": {"code": "bad_request", "message": message}}
    response = JsonResponse(body, status=400)
    response["Cache-Control"] = "no-store"
    return response


def validation_failed(errors: dict[str, list[str]]) -> HttpResponse:
    """Return a uniform 400 ``validation_failed`` envelope (see contract §6)."""
    body = {
        "error": {
            "code": "validation_failed",
            "message": "One or more fields are invalid.",
            "fields": errors,
        }
    }
    response = JsonResponse(body, status=400)
    response["Cache-Control"] = "no-store"
    return response


def not_found_response() -> HttpResponse:
    response = JsonResponse(_NOT_FOUND_BODY, status=404)
    response["Cache-Control"] = "no-store"
    return response


def parse_json_body(request: HttpRequest) -> dict[str, Any] | HttpResponse:
    """Decode ``request.body`` as a JSON object.

    Returns the parsed ``dict`` on success or a 400 ``HttpResponse`` on
    failure. Anything other than a top-level JSON object (e.g., an
    array, scalar, or empty body) is rejected.
    """
    raw = request.body or b""
    if not raw:
        return {}
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return bad_request("Request body must be valid UTF-8 JSON.")
    if not isinstance(decoded, dict):
        return bad_request("Request body must be a JSON object.")
    return decoded


def writable_field_names(
    model: type[Model],
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model | None,
) -> list[str]:
    """Compute the writable field set for create or update.

    Mirrors ``DetailView._visible_field_names`` minus
    ``get_readonly_fields``. Sensitive-named fields are dropped as
    defense-in-depth (``ACCEPTANCE.md`` §4.7 S-31).
    """
    declared = list(model_admin.get_fields(request, obj) or ())
    excluded = set(model_admin.get_exclude(request, obj) or ())
    readonly = set(model_admin.get_readonly_fields(request, obj) or ())
    out: list[str] = []
    for name in declared:
        if name in excluded:
            continue
        if name in readonly:
            continue
        if is_sensitive_field_name(name):
            continue
        # M2M is "unsupported" in v1 (contract §4); exclude from writes.
        try:
            model_field = model._meta.get_field(name)
        except Exception:
            model_field = None
        if isinstance(model_field, ManyToManyField):
            continue
        out.append(name)
    return filter_sensitive(out)


def readonly_or_excluded_names(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model | None,
) -> set[str]:
    """Names a payload is *forbidden* to mention (readonly + exclude)."""
    excluded = set(model_admin.get_exclude(request, obj) or ())
    readonly = set(model_admin.get_readonly_fields(request, obj) or ())
    return excluded | readonly


def reject_forbidden_keys(
    payload: dict[str, Any],
    writable: list[str],
    forbidden: set[str],
) -> HttpResponse | None:
    """Return a 400 if any key in ``payload`` is unknown or forbidden.

    Per contract §5.2: writes to readonly/excluded are a ``bad_request``.
    Per contract §5.1: unknown keys are also a ``bad_request``.
    """
    writable_set = set(writable)
    for key in payload:
        if key in forbidden:
            return bad_request(f"Field {key!r} is read-only.")
        if is_sensitive_field_name(key):
            # Defense-in-depth: never let a payload mention a denied name.
            return bad_request(f"Field {key!r} is not writable.")
        if key not in writable_set:
            return bad_request(f"Unknown field {key!r}.")
    return None


def coerce_fk_values(
    payload: dict[str, Any],
    model: type[Model],
) -> dict[str, Any]:
    """Translate FK keys from ``{"id": pk, "label": ...}`` envelope to bare pk.

    The wire contract sends FKs as ``{"id": pk, "label": str}`` on read
    (§4) and accepts bare pk on write (§5.1). Some clients may echo the
    envelope back unchanged — be tolerant: if the value is a dict with
    an ``id`` key, use that. Otherwise pass through.
    """
    out: dict[str, Any] = {}
    for key, value in payload.items():
        try:
            model_field = model._meta.get_field(key)
        except Exception:
            out[key] = value
            continue
        if isinstance(model_field, ForeignKey) and isinstance(value, dict) and "id" in value:
            out[key] = value["id"]
            continue
        out[key] = value
    return out


def form_errors_to_envelope(form: Any) -> dict[str, list[str]]:
    """Convert a Django form's ``errors`` mapping to the wire shape.

    Non-field errors are surfaced under the empty-string key (matches
    Django's own ``__all__`` convention, but normalized for clients).
    """
    errors: dict[str, list[str]] = {}
    for field_name, error_list in form.errors.items():
        key = "" if field_name == "__all__" else field_name
        errors[key] = [str(e) for e in error_list]
    return errors


def merged_initial_for_update(
    obj: Model,
    writable: list[str],
    payload: dict[str, Any],
    model: type[Model],
) -> dict[str, Any]:
    """Build the form data for a PATCH: existing values overlaid with payload.

    The form behaves like a full POST: every writable field gets a
    starting value (the current instance's), and the payload merges on
    top. This is what Django's admin does for change-views.
    """
    merged: dict[str, Any] = {}
    for name in writable:
        current = getattr(obj, name, None)
        try:
            model_field = model._meta.get_field(name)
        except Exception:
            model_field = None
        if isinstance(model_field, ForeignKey):
            # Forms expect FK values as the related-pk (``<name>_id``).
            merged[name] = getattr(obj, f"{name}_id", None)
        else:
            merged[name] = current
    coerced = coerce_fk_values(payload, model)
    merged.update(coerced)
    return merged
