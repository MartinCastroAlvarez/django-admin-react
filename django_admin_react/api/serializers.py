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
from django.utils.safestring import SafeString

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
    # SafeString FIRST — it subclasses ``str``, so it must be detected
    # before the plain-``str`` pass-through below. A ``SafeString`` is
    # produced by ``format_html`` / ``mark_safe``, which is how a
    # ``ModelAdmin`` ``list_display`` method (or a readonly display
    # method) opts a value into being rendered as HTML in Django's own
    # changelist. We mirror that: emit a typed ``{"html": ...}``
    # envelope so the SPA renders it as markup. A *plain* ``str`` —
    # e.g. a ``CharField`` containing ``"<script>"`` — is NOT a
    # ``SafeString`` and stays inert text (rendered escaped by React).
    # Trust boundary is identical to Django's: the admin author marked
    # it safe; interpolated args in ``format_html`` are auto-escaped.
    # See docs/api-contract.md §4 + SECURITY.md (Closes #172).
    if isinstance(value, SafeString):
        return {"html": str(value)}
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
    if _looks_like_range(value):
        # PostgreSQL range fields. The structured envelope is documented
        # in docs/api-contract.md §4 (Closes #141 — contract used to say
        # this but no code emitted it; the str() fallback below emitted
        # the psycopg ``Range.__str__`` form instead).
        return _serialize_range_value(value, field)
    if isinstance(value, Model):
        return {"id": value.pk, "label": label_for(value)}
    return str(value)


# --------------------------------------------------------------------------- #
# PostgreSQL range support — see docs/api-contract.md §4 (Closes #141).      #
# --------------------------------------------------------------------------- #
_RANGE_SUBTYPE_BY_INTERNAL: Final[dict[str, str]] = {
    "DateRangeField": "daterange",
    "DateTimeRangeField": "datetimerange",
    "DecimalRangeField": "numrange",
    "IntegerRangeField": "intrange",
    "BigIntegerRangeField": "intrange",
}


def _looks_like_range(value: Any) -> bool:
    """Duck-test for a psycopg ``Range``-shaped value.

    ``psycopg2.extras.Range`` and ``psycopg.types.range.Range`` both
    expose ``lower``, ``upper``, ``lower_inc``, ``upper_inc``,
    ``isempty``. We duck-type rather than ``isinstance`` so the
    package never imports psycopg at module load — the consumer's
    ``django.contrib.postgres`` install transitively makes it
    available at runtime when needed, and the test suite can mint
    Range-shaped fixtures without forcing psycopg as a dev
    dependency.
    """
    return all(
        hasattr(value, attr) for attr in ("lower", "upper", "lower_inc", "upper_inc", "isempty")
    )


def _serialize_range_value(value: Any, field: Field | None) -> dict[str, Any]:
    """Build the structured range envelope documented in api-contract §4.

    Closes [#141]. The contract specifies:

    .. code-block:: json

        {"subtype": "daterange"|"datetimerange"|"intrange"|"numrange",
         "value": {"lower": ..., "upper": ..., "bounds": "[)"},
         "empty": true   // only when value is None}

    ``subtype`` derives from the field's Django internal type so the
    SPA can pick the right inner widget (date vs. datetime vs.
    number); without a ``field`` hint we fall back to the generic
    ``"range"`` label that ``field_type_for`` already uses for the
    type-mapping. ``bounds`` is reconstructed from ``lower_inc`` /
    ``upper_inc`` because that's the portable representation across
    psycopg2 and psycopg3 (both libraries expose those booleans;
    only psycopg2 exposes the private ``_bounds`` string directly).
    The closed four-char vocabulary is ``"[]"``, ``"[)"``, ``"(]"``,
    ``"()"`` — the same vocabulary the contract documents.
    """
    subtype = "range"
    if field is not None:
        subtype = _RANGE_SUBTYPE_BY_INTERNAL.get(field.get_internal_type(), "range")
    if bool(getattr(value, "isempty", False)):
        return {"subtype": subtype, "value": None, "empty": True}
    lower_char = "[" if value.lower_inc else "("
    upper_char = "]" if value.upper_inc else ")"
    return {
        "subtype": subtype,
        "value": {
            "lower": serialize_value(value.lower),
            "upper": serialize_value(value.upper),
            "bounds": lower_char + upper_char,
        },
    }


def serialize_fk_value(value: Model | None, *, admin_site: Any = None) -> dict[str, Any] | None:
    """Serialize an FK as ``{"id": pk, "label": str(obj)}`` or ``None``.

    When ``admin_site`` is provided **and** the related model is
    registered on it, the envelope also carries
    ``to: {"app_label": <real>, "model_name": ...}`` so the SPA can
    render the cell as a navigable link to the related object's detail
    page (#184). The target is **omitted** when the related model isn't
    registered — surfacing a link the detail endpoint would 404 on (and
    leaking adjacency to an unregistered model) is the exact posture
    #89 removed from filter descriptors. ``app_label`` is the real
    ``_meta.app_label`` the detail URL resolves against.
    """
    if value is None:
        return None
    out: dict[str, Any] = {"id": value.pk, "label": label_for(value)}
    if admin_site is not None and type(value) in getattr(admin_site, "_registry", {}):
        meta = value._meta
        out["to"] = {"app_label": meta.app_label, "model_name": meta.model_name}
    return out


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
        field = model_or_instance._meta.get_field(name)
    except Exception:
        return None
    # ``get_field`` may also return reverse relations / generic FKs,
    # which are not concrete ``Field``s. Callers want a real field or
    # nothing (those names fall through to the callable/display path).
    return field if isinstance(field, Field) else None


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
    "FileField": "file",
    "FilePathField": "filepath",
    "FloatField": "float",
    "ForeignKey": "foreignkey",
    "GenericIPAddressField": "ip",
    "IPAddressField": "ip",
    "ImageField": "image",
    "IntegerField": "integer",
    "JSONField": "json",
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

    1. ``ManyToManyField`` → ``"manytomany"`` (Issue #55).
    2. ``ImageField`` → ``"image"`` (subclass of FileField; Django
       reports ``get_internal_type()`` as ``"FileField"`` so the
       isinstance check is the only way to distinguish).
    3. The closed vocabulary in ``_TYPE_BY_INTERNAL``.
    4. Custom types registered via ``register_field_type``.
    5. ``"unsupported"`` — the SPA renders a read-only label.
    """
    if isinstance(field, ManyToManyField):
        return "manytomany"
    # ImageField check must precede the internal_type lookup.
    # Import locally to avoid a hard Pillow dependency at module
    # load time.
    from django.db.models import ImageField as _ImageField

    if isinstance(field, _ImageField):
        return "image"
    internal = field.get_internal_type()
    if internal in _TYPE_BY_INTERNAL:
        return _TYPE_BY_INTERNAL[internal]
    return _CUSTOM_TYPE_BY_INTERNAL.get(internal, "unsupported")


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
    if isinstance(field, ForeignKey | ManyToManyField):
        # FK and M2M both reference a related model. The SPA uses
        # ``to`` to wire autocomplete (#59) and to render the FK/M2M
        # picker. For M2M-with-through-extras the field stays
        # readonly via writable_field_names; ``to`` still points at
        # the target so the SPA can render the existing labels.
        related = field.related_model
        # ``related_model`` is the resolved model class by the time the
        # admin is loaded; the ``"self"`` sentinel only exists during
        # model definition. Guard it out so the type narrows cleanly.
        if related is not None and not isinstance(related, str):
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
