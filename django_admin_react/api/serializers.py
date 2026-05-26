"""Conservative field serialization.

The wire format is described in ``docs/api-contract.md`` §4. This module
converts Python / Django values into the JSON payload, after the admin
form's exclusion rules have been applied. The sensitive-name denylist
below is defense-in-depth on top of those rules.

Rules (binding; see ``ACCEPTANCE.md`` §3.5 and §4.7):

- Pass-through: ``str``, ``int``, ``float``, ``bool``, ``None``.
- ``Decimal``, ``UUID``, ``date``, ``datetime``, ``time`` → string forms.
- ``ForeignKey`` → ``{"id": pk, "label": str(related)}``.
- ``ManyToMany`` → ``"unsupported"`` v1.
- Anything else → ``str(value)`` (never raises).
- Field names matching the denylist are never emitted.
"""

from __future__ import annotations

import datetime as _dt
import decimal
import uuid
from collections.abc import Iterable
from typing import Any
from typing import Final

from django.db.models import Field
from django.db.models import ForeignKey
from django.db.models import ManyToManyField
from django.db.models import Model

SENSITIVE_NAME_SUBSTRINGS: Final[tuple[str, ...]] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "hash",
    "private_key",
    "session",
    "nonce",
    "salt",
)


def is_sensitive_field_name(name: str) -> bool:
    """Return True iff ``name`` matches any entry in the denylist."""
    if not isinstance(name, str):
        return True
    lowered = name.lower()
    return any(s in lowered for s in SENSITIVE_NAME_SUBSTRINGS)


def filter_sensitive(names: Iterable[str]) -> list[str]:
    """Drop any field name that matches the denylist."""
    return [n for n in names if not is_sensitive_field_name(n)]


def serialize_value(value: Any) -> Any:
    """Convert a Python value to its JSON-compatible wire form."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, _dt.time):
        return value.isoformat()
    if isinstance(value, Model):
        return {"id": value.pk, "label": label_for(value)}
    return str(value)


def serialize_fk_value(value: Model | None) -> dict[str, Any] | None:
    """Serialize an FK as ``{"id": pk, "label": str(obj)}`` or ``None``."""
    if value is None:
        return None
    return {"id": value.pk, "label": label_for(value)}


def label_for(obj: Model) -> str:
    """Return a human-readable label for ``obj`` (``str(obj)`` with fallback).

    Django models that raise on ``__str__`` (e.g. missing related rows
    during a half-migrated state) would otherwise crash a list page.
    The fallback ``<ClassName: pk>`` keeps the UI responsive and never
    raises.

    Centralized here so the views, the registry payload, and the
    serializer label objects identically — a UX win and a single
    point of defense for ``__str__`` exceptions.
    """
    try:
        return str(obj)
    except Exception:
        return f"<{obj.__class__.__name__}: {obj.pk}>"


_TYPE_BY_INTERNAL: Final[dict[str, str]] = {
    "AutoField": "integer",
    "BigAutoField": "integer",
    "BigIntegerField": "integer",
    "BooleanField": "boolean",
    "CharField": "string",
    "DateField": "date",
    "DateTimeField": "datetime",
    "DecimalField": "decimal",
    "EmailField": "email",
    "FloatField": "float",
    "ForeignKey": "foreignkey",
    "IntegerField": "integer",
    "OneToOneField": "foreignkey",
    "PositiveBigIntegerField": "integer",
    "PositiveIntegerField": "integer",
    "PositiveSmallIntegerField": "integer",
    "SlugField": "slug",
    "SmallIntegerField": "integer",
    "TextField": "text",
    "TimeField": "time",
    "URLField": "url",
    "UUIDField": "uuid",
}


def field_type_for(field: Field) -> str:
    """Closed v1-vocabulary type for a Django model field."""
    if isinstance(field, ManyToManyField):
        return "unsupported"
    internal = field.get_internal_type()
    return _TYPE_BY_INTERNAL.get(internal, "unsupported")


def field_choices(field: Field) -> list[dict[str, Any]] | None:
    choices = getattr(field, "choices", None)
    if not choices:
        return None
    return [{"value": v, "label": str(lbl)} for v, lbl in choices]


def field_metadata(
    field: Field,
    *,
    label: str,
    required: bool,
    readonly: bool,
    help_text: str,
    value: Any,
) -> dict[str, Any]:
    """Per-field metadata block for the detail endpoint."""
    type_ = field_type_for(field)
    metadata: dict[str, Any] = {
        "type": type_,
        "label": label,
        "required": required,
        "readonly": readonly,
        "help_text": help_text,
        "value": value,
    }
    if isinstance(field, ForeignKey):
        related = field.related_model
        if related is not None:
            meta = related._meta
            metadata["to"] = {"app_label": meta.app_label, "model_name": meta.model_name}
    if getattr(field, "max_length", None):
        metadata["max_length"] = field.max_length
    if type_ == "decimal":
        metadata["decimal_places"] = getattr(field, "decimal_places", None)
    choices = field_choices(field)
    if choices is not None:
        metadata["type"] = "choice"
        metadata["choices"] = choices
    return metadata
