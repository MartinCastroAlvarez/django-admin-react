"""Conservative field serialization.

The wire format is described in ``docs/api-contract.md`` §4. This module
converts Python / Django values into the JSON payload, after the admin
form's exclusion rules have been applied. The sensitive-name denylist
below is defense-in-depth on top of those rules.

Rules (binding; see ``ACCEPTANCE.md`` §3.5 and §4.7):

- Pass-through: ``str``, ``int``, ``float``, ``bool``, ``None``.
- ``Decimal``, ``UUID``, ``date``, ``datetime``, ``time`` → string forms.
- ``ForeignKey`` → ``{"id": pk, "label": str(related)}``.
- ``ManyToMany`` (plain) → ``[{"id": pk, "label": str(related)}, ...]``
  capped at ``M2M_VALUE_CAP`` items; oversize sets return
  ``{"sample": [...], "count": N, "truncated": true}``.
- ``ManyToMany`` (with non-auto ``through``) → ``readonly`` hint;
  write attempts on these are rejected at the ``writable_field_names``
  stage.
- Anything else → ``str(value)`` (never raises).
- Field names matching the denylist are never emitted.
"""

from __future__ import annotations

import base64
import datetime as _dt
import decimal
import uuid
from collections.abc import Callable
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


def serialize_value(value: Any, field: Field | None = None) -> Any:
    """Convert a Python value to its JSON-compatible wire form.

    When ``field`` is provided and its internal type was registered via
    ``register_field_type`` with a custom serializer, that serializer
    runs *instead of* the default Python-type dispatch below. This is
    the consumer extension point for custom field types whose
    ``str(value)`` representation is not the wire form the SPA wants.
    """
    if field is not None:
        custom = _registered_serializer(field)
        if custom is not None:
            return custom(value)
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
    if isinstance(value, _dt.timedelta):
        # ISO 8601 duration via ``str(td)`` is "H:MM:SS[.ffffff]" —
        # not strictly ISO 8601, but stable and round-trippable via
        # ``datetime.timedelta`` parsing on the consumer side. Use
        # ``total_seconds()`` as the canonical numeric form too.
        return str(value)
    if isinstance(value, bytes | bytearray | memoryview):
        # BinaryField values: base64-encode for JSON safety. The wire
        # contract documents this so the SPA knows to decode.
        return base64.b64encode(bytes(value)).decode("ascii")
    if isinstance(value, list | tuple):
        # PostgreSQL ArrayField, plain Python lists from custom getters.
        # Recursively serialize each element so nested types (e.g.
        # ``ArrayField(DateField())``) still round-trip cleanly.
        return [serialize_value(v) for v in value]
    if isinstance(value, dict):
        # JSONField: pass through, but recursively serialize values
        # in case the dict carries e.g. dates that JSON would reject.
        return {str(k): serialize_value(v) for k, v in value.items()}
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


def safe_get_field(model_or_instance: type[Model] | Model, name: str) -> Field | None:
    """Return ``_meta.get_field(name)`` or ``None`` if there is no such field.

    Accepts either a model class or a model instance — both expose
    ``_meta`` and Django dispatches identically. Returning ``None``
    lets callers branch cleanly on "is this a real field?" without
    knowing that ``get_field`` raises ``FieldDoesNotExist``.

    Centralized so the read/write code paths that need this lookup
    share one implementation; previously each had a private copy,
    which is one bug fix in three places (see
    ``docs/architect-verdict-2026-05-26.md`` Condition A).
    """
    try:
        return model_or_instance._meta.get_field(name)
    except Exception:
        return None


_TYPE_BY_INTERNAL: Final[dict[str, str]] = {
    "AutoField": "integer",
    "BigAutoField": "integer",
    "BigIntegerField": "integer",
    "BinaryField": "binary",
    "BooleanField": "boolean",
    "CharField": "string",
    "DateField": "date",
    "DateTimeField": "datetime",
    "DecimalField": "decimal",
    "DurationField": "duration",
    "EmailField": "email",
    "FilePathField": "filepath",
    "FloatField": "float",
    "ForeignKey": "foreignkey",
    "GenericIPAddressField": "ip",
    "IPAddressField": "ip",
    "IntegerField": "integer",
    "JSONField": "json",
    "ManyToManyField": "many_to_many",
    "OneToOneField": "foreignkey",
    "PositiveBigIntegerField": "integer",
    "PositiveIntegerField": "integer",
    "PositiveSmallIntegerField": "integer",
    "SlugField": "slug",
    "SmallIntegerField": "integer",
    "SmallAutoField": "integer",
    "TextField": "text",
    "TimeField": "time",
    "URLField": "url",
    "UUIDField": "uuid",
    # PostgreSQL contrib fields. Listed by internal-type name so the
    # consumer doesn't need to import ``django.contrib.postgres`` for
    # the lookup table to be useful.
    "ArrayField": "array",
    "HStoreField": "json",
    "DateRangeField": "range",
    "DateTimeRangeField": "range",
    "DecimalRangeField": "range",
    "IntegerRangeField": "range",
    "BigIntegerRangeField": "range",
}

# Soft cap on the number of related rows embedded in an M2M field's
# ``value``. Beyond this, the detail response returns the
# ``{sample, count, truncated}`` envelope and the SPA paginates via
# the related model's list endpoint. 100 keeps p99 detail payloads
# bounded without making the common case (small tag set, role
# membership) feel artificially limited.
M2M_VALUE_CAP: Final[int] = 100


# Extension surface: consumers register a custom field type via
# ``register_field_type`` (see below). Both maps are checked *after*
# the closed v1 vocabulary so a consumer cannot accidentally redefine
# a builtin type and surprise the SPA. The custom registry is
# distinct from ``_TYPE_BY_INTERNAL`` so an audit of the closed
# vocabulary stays trivial.
_CUSTOM_TYPE_BY_INTERNAL: dict[str, str] = {}
_CUSTOM_SERIALIZERS: dict[str, Callable[[Any], Any]] = {}


def register_field_type(
    internal_type: str,
    vocab_type: str,
    serializer: Callable[[Any], Any] | None = None,
) -> None:
    """Register a custom Django field type so the API serializes it.

    Call this once at app start (e.g. in your ``AppConfig.ready``):

    ::

        from django_admin_react.api.serializers import register_field_type
        from .fields import MoneyField

        register_field_type(
            "MoneyField",
            "decimal",
            serializer=lambda v: None if v is None else str(v.amount),
        )

    ``internal_type`` is what ``field.get_internal_type()`` returns —
    typically the class name. ``vocab_type`` is the wire-type label
    the SPA branches on; reuse one of the existing labels
    (``string``, ``integer``, ``json``, ``array``, …) so the SPA can
    render it without code changes, or coin a new label and ship a
    matching frontend widget via the extension surface.

    Builtin types in ``_TYPE_BY_INTERNAL`` cannot be redefined — calling
    this on a builtin internal type silently no-ops. That's
    intentional: a third-party app shouldn't be able to change how the
    SPA renders ``CharField`` for every consumer.

    ``serializer``, if provided, runs *instead of* the default
    ``serialize_value`` for instances of this field. Use it when
    ``str(value)`` is not a useful wire form (e.g., a custom value
    object needs its ``.amount`` extracted).
    """
    if internal_type in _TYPE_BY_INTERNAL:
        return
    _CUSTOM_TYPE_BY_INTERNAL[internal_type] = vocab_type
    if serializer is not None:
        _CUSTOM_SERIALIZERS[internal_type] = serializer


def _registered_serializer(field: Field) -> Callable[[Any], Any] | None:
    """Return a custom serializer for ``field``, if one was registered."""
    return _CUSTOM_SERIALIZERS.get(field.get_internal_type())


def field_type_for(field: Field) -> str:
    """Closed v1-vocabulary type for a Django model field.

    Resolution order:

    1. The closed vocabulary in ``_TYPE_BY_INTERNAL`` (includes
       ``many_to_many`` for ``ManyToManyField`` — closes #55).
    2. Custom types registered via ``register_field_type`` (#60).
    3. ``"unsupported"`` — the SPA renders a read-only label.
    """
    internal = field.get_internal_type()
    if internal in _TYPE_BY_INTERNAL:
        return _TYPE_BY_INTERNAL[internal]
    return _CUSTOM_TYPE_BY_INTERNAL.get(internal, "unsupported")


def is_plain_m2m(field: Field) -> bool:
    """Return True iff ``field`` is a ``ManyToManyField`` whose ``through``
    model is auto-created (no extra fields on the join row).

    Django auto-creates a through model for every plain
    ``ManyToManyField`` declaration. When the admin author explicitly
    declares ``through=<Model>`` (typically to attach extra fields like
    ``date_added``, ``role``), the through model is **not**
    auto-created — its ``_meta.auto_created`` is ``False``.

    The package supports plain M2Ms for read **and** write in v1.
    Through-with-extras M2Ms are surfaced read-only; writes against
    them are rejected at ``writable_field_names``. This keeps the
    write path honest — we never silently drop the extra fields on
    the join row.
    """
    if not isinstance(field, ManyToManyField):
        return False
    through = getattr(field.remote_field, "through", None)
    if through is None:
        return True
    return bool(getattr(through._meta, "auto_created", False))


def serialize_m2m_value(
    field: ManyToManyField,
    instance: Model,
    *,
    cap: int | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Serialize the current set of related rows for an M2M field.

    Returns a plain ``list[{id, label}]`` when the related queryset
    has at most ``cap`` rows. Beyond ``cap``, returns the truncated
    envelope ``{"sample": [...], "count": N, "truncated": true}`` so
    the SPA can render a meaningful read state without forcing
    detail pages to materialize unbounded sets (a moderation
    workflow with 10K tagged users would otherwise N+1 in the
    browser).

    Defense in depth: any exception raised by the manager (broken
    descriptor, half-migrated state) collapses to ``[]`` rather than
    500-ing the detail response. The list endpoint and write path
    have their own permission gates; serializing an empty value
    here never leaks anything.
    """
    # Resolve the cap at call time (not at function-definition time) so
    # tests can monkey-patch the module-level constant via ``mock.patch``.
    effective_cap = cap if cap is not None else M2M_VALUE_CAP
    try:
        manager = getattr(instance, field.name)
        queryset = manager.all()
        count = queryset.count()
        if count <= effective_cap:
            return [{"id": obj.pk, "label": label_for(obj)} for obj in queryset]
        sample = [{"id": obj.pk, "label": label_for(obj)} for obj in queryset[:effective_cap]]
        return {"sample": sample, "count": count, "truncated": True}
    except Exception:
        return []


def field_choices(field: Field) -> list[dict[str, Any]] | None:
    """Serialize a Django field's ``choices`` as a list of ``{value, label}``.

    Returns ``None`` when the field has no choices (so the wire payload
    omits the key entirely rather than emitting a misleading empty
    list). Labels are coerced via ``str(...)`` so lazy translation
    proxies resolve to the request locale before serialization.
    """
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
    if isinstance(field, ManyToManyField):
        related = field.related_model
        if related is not None:
            meta = related._meta
            metadata["to"] = {"app_label": meta.app_label, "model_name": meta.model_name}
        # ``through`` is ``null`` for plain M2M, ``{app_label, model_name}``
        # for explicit through-with-extras. The SPA uses this to choose
        # between "edit the relation directly" and "edit via the through
        # model's admin" (the readonly hint).
        through = getattr(field.remote_field, "through", None)
        if through is not None and not getattr(through._meta, "auto_created", False):
            metadata["through"] = {
                "app_label": through._meta.app_label,
                "model_name": through._meta.model_name,
            }
        else:
            metadata["through"] = None
    if getattr(field, "max_length", None):
        metadata["max_length"] = field.max_length
    if type_ == "decimal":
        metadata["decimal_places"] = getattr(field, "decimal_places", None)
    choices = field_choices(field)
    if choices is not None:
        metadata["type"] = "choice"
        metadata["choices"] = choices
    return metadata
