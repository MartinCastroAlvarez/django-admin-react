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

Public surface — every view layer should reach for one of these first:

- :func:`bad_request`            — uniform 400 envelope.
- :func:`validation_failed`      — uniform 400 with per-field errors.
- :func:`not_found_response`     — canonical 404 envelope.
- :func:`parse_json_body`        — decode a JSON object or return 400.
- :func:`load_object_or_none`    — fetch through ``get_queryset`` or
                                   return ``None`` (caller emits 404).
- :func:`writable_field_names`   — fields the API will accept on write.
- :func:`readonly_or_excluded_names`
                                 — fields the payload may not mention.
- :func:`reject_forbidden_keys`  — payload-shape validation gate.
- :func:`coerce_fk_values`       — accept FK envelope on input.
- :func:`form_errors_to_envelope`
                                 — Django form errors → wire shape.
- :func:`merged_initial_for_update`
                                 — instance + payload → form data.
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
from django_admin_react.api.serializers import safe_get_field

# Canonical 404 body. Deliberately omits the requested app/model/pk —
# leaking those would give an attacker an oracle for what *would* have
# existed had they been authorized. See ``SECURITY.md`` §3 rule 12.
_NOT_FOUND_BODY: dict[str, Any] = {
    "error": {"code": "not_found", "message": "Not found."},
}


# --------------------------------------------------------------------------- #
# Response factories                                                          #
# --------------------------------------------------------------------------- #
def bad_request(message: str = "Malformed request.") -> HttpResponse:
    """Return the package's canonical 400 ``bad_request`` envelope.

    The ``message`` is safe to surface to the client; never include
    request-derived strings here unless they are ``repr()``-quoted
    (``SECURITY.md`` §3 rule 12).
    """
    body = {"error": {"code": "bad_request", "message": message}}
    response = JsonResponse(body, status=400)
    response["Cache-Control"] = "no-store"
    return response


def validation_failed(errors: dict[str, list[str]]) -> HttpResponse:
    """Return a 400 ``validation_failed`` envelope (contract §6).

    The ``errors`` mapping is already the wire shape — see
    :func:`form_errors_to_envelope` for the canonical converter from
    Django's ``form.errors`` to this shape.
    """
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
    """Return the package's canonical 404 envelope (contract §6).

    Single source of truth for 404 bodies across the view layer; every
    view that needs to emit a 404 imports this rather than rolling its
    own envelope (keeps the leak surface to zero, per
    ``SECURITY.md`` §3 rule 12).
    """
    response = JsonResponse(_NOT_FOUND_BODY, status=404)
    response["Cache-Control"] = "no-store"
    return response


# --------------------------------------------------------------------------- #
# Request / object lookup                                                     #
# --------------------------------------------------------------------------- #
def parse_json_body(request: HttpRequest) -> dict[str, Any] | HttpResponse:
    """Decode ``request.body`` as a JSON object, or return a 400.

    Returns:
        - ``{}`` if the body is empty (PATCH with no fields is valid).
        - The parsed dict on success.
        - A ``HttpResponse`` (400) if the body is invalid UTF-8, invalid
          JSON, or not a JSON object (arrays, scalars, etc. are
          rejected — the contract only ever speaks objects).

    Callers check ``isinstance(result, HttpResponse)`` to branch.
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


def load_object_or_none(
    model: type[Model],
    model_admin: ModelAdmin,
    request: HttpRequest,
    pk: Any,
) -> Model | None:
    """Fetch one row through the admin's queryset, or ``None`` on miss.

    Three lookup failures collapse to ``None`` (callers convert to
    404, never to 500):

    - ``DoesNotExist`` — pk valid but no matching row, or the row was
      filtered out by ``ModelAdmin.get_queryset(request)``.
    - ``ValueError`` — pk could not be parsed for the field's type
      (e.g., ``"abc"`` against an ``IntegerField``).
    - ``TypeError`` — similar parse failure for a custom pk type.

    Centralizing this here means every "load or 404" call site has
    the same exception surface and the same security posture
    (queryset never bypassed, parse errors never leak).
    """
    try:
        return model_admin.get_queryset(request).get(pk=pk)
    except (model.DoesNotExist, ValueError, TypeError):
        return None


# --------------------------------------------------------------------------- #
# Field-set computation                                                       #
# --------------------------------------------------------------------------- #
def writable_field_names(
    model: type[Model],
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model | None,
) -> list[str]:
    """Field names the API will accept in a create or update payload.

    Computed as ``get_fields`` minus ``get_exclude`` minus
    ``get_readonly_fields`` minus the sensitive-name denylist
    (``ACCEPTANCE.md`` §4.7 S-31) minus ``ManyToManyField``
    (unsupported in v1 per ``docs/api-contract.md`` §4).

    Defense-in-depth: even if a ``ModelAdmin`` author forgets to
    ``exclude`` a sensitive-named field, the substring match keeps
    it out of the writable set.
    """
    declared = list(model_admin.get_fields(request, obj) or ())
    excluded = set(model_admin.get_exclude(request, obj) or ())
    readonly = set(model_admin.get_readonly_fields(request, obj) or ())
    out: list[str] = []
    for name in declared:
        if name in excluded or name in readonly or is_sensitive_field_name(name):
            continue
        if isinstance(safe_get_field(model, name), ManyToManyField):
            continue
        out.append(name)
    return filter_sensitive(out)


def readonly_or_excluded_names(
    model_admin: ModelAdmin,
    request: HttpRequest,
    obj: Model | None,
) -> set[str]:
    """Field names a payload may not even mention.

    Used by :func:`reject_forbidden_keys` to emit the precise message
    ``"Field 'x' is read-only."`` instead of the generic
    ``"Unknown field 'x'."`` when the admin marks a field as
    readonly or excluded. Both responses are 400 per contract §5;
    the distinction is a UX courtesy for the SPA.
    """
    excluded = set(model_admin.get_exclude(request, obj) or ())
    readonly = set(model_admin.get_readonly_fields(request, obj) or ())
    return excluded | readonly


# --------------------------------------------------------------------------- #
# Payload validation                                                          #
# --------------------------------------------------------------------------- #
def reject_forbidden_keys(
    payload: dict[str, Any],
    writable: list[str],
    forbidden: set[str],
) -> HttpResponse | None:
    """Validate the shape of a write payload — return a 400 or ``None``.

    Three rejection reasons, each yielding ``bad_request`` per
    ``docs/api-contract.md`` §6:

    1. The key is read-only or excluded by the admin (§5.2).
    2. The key matches the sensitive-name denylist
       (defense-in-depth, even if the admin's ``writable`` list let
       it through somehow).
    3. The key is not in ``writable`` at all (§5.1, unknown field).

    Rejecting *before* form construction means a hostile payload
    cannot trigger ``ModelForm`` side effects (e.g. FK queries) on
    field names the admin never declared.
    """
    writable_set = set(writable)
    for key in payload:
        if key in forbidden:
            return bad_request(f"Field {key!r} is read-only.")
        if is_sensitive_field_name(key):
            return bad_request(f"Field {key!r} is not writable.")
        if key not in writable_set:
            return bad_request(f"Unknown field {key!r}.")
    return None


def coerce_fk_values(
    payload: dict[str, Any],
    model: type[Model],
) -> dict[str, Any]:
    """Normalize ForeignKey values to the bare pk the form layer expects.

    The wire contract sends FKs *out* as ``{"id": pk, "label": str}``
    (§4) but accepts bare pk *in* (§5.1). Clients that echo the read
    shape back would otherwise hit a form-validation error even when
    their intent is clear. Recognizing the envelope on input keeps
    the SPA's edit-in-place flow honest without weakening
    validation — Django will still reject any pk that does not
    resolve to a real related row.
    """
    out: dict[str, Any] = {}
    for key, value in payload.items():
        model_field = safe_get_field(model, key)
        is_fk_envelope = (
            isinstance(model_field, ForeignKey) and isinstance(value, dict) and "id" in value
        )
        out[key] = value["id"] if is_fk_envelope else value
    return out


def form_errors_to_envelope(form: Any) -> dict[str, list[str]]:
    """Convert a Django form's ``errors`` mapping to the wire shape.

    Non-field errors are surfaced under the empty-string key
    (normalized from Django's ``__all__`` convention so clients
    don't have to know that magic name).
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
    """Build the ``data`` dict for a PATCH form: instance values + payload.

    Django ``ModelForm`` validates the whole form on every save, even
    on partial updates. We therefore seed every writable field with
    the instance's current value, then overlay the user-supplied
    payload. This mirrors what Django admin's change-view does.

    FK fields are seeded with ``<name>_id`` because that is the wire
    shape the form's choice field expects — passing the related
    instance directly would trigger an extra DB query on a hot path.
    """
    merged: dict[str, Any] = {}
    for name in writable:
        if isinstance(safe_get_field(model, name), ForeignKey):
            merged[name] = getattr(obj, f"{name}_id", None)
        else:
            merged[name] = getattr(obj, name, None)
    merged.update(coerce_fk_values(payload, model))
    return merged
