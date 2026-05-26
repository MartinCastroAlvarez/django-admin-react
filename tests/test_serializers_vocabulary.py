"""Tests for the field-type vocabulary expansion (Issue #60).

Covered:

- New entries in ``_TYPE_BY_INTERNAL``: ``JSONField``, ``DurationField``,
  ``GenericIPAddressField``, ``BinaryField``, ``FilePathField``,
  ``SmallAutoField``, plus PostgreSQL contrib fields (``ArrayField``,
  ``HStoreField``, the range types).
- ``serialize_value`` round-trips the new Python types
  (``timedelta``, ``bytes``, ``list``, ``dict``).
- ``register_field_type`` extension hook lets a consumer add a custom
  field-type mapping + a custom serializer.
- Builtin types cannot be overridden by ``register_field_type``
  (silent no-op — keeps the closed vocabulary stable).
"""

from __future__ import annotations

import base64
import datetime as dt
from collections.abc import Iterator

import pytest
from django.db import models

from django_admin_react.api.serializers import _CUSTOM_SERIALIZERS
from django_admin_react.api.serializers import _CUSTOM_TYPE_BY_INTERNAL
from django_admin_react.api.serializers import field_type_for
from django_admin_react.api.serializers import register_field_type
from django_admin_react.api.serializers import serialize_value


# --------------------------------------------------------------------------- #
# Fixtures: a clean custom-type registry for each test                        #
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _reset_custom_registry() -> Iterator[None]:
    """Snapshot + restore the custom-type registry around each test.

    Avoids state leakage between tests that call ``register_field_type``.
    """
    saved_types = dict(_CUSTOM_TYPE_BY_INTERNAL)
    saved_serializers = dict(_CUSTOM_SERIALIZERS)
    yield
    _CUSTOM_TYPE_BY_INTERNAL.clear()
    _CUSTOM_TYPE_BY_INTERNAL.update(saved_types)
    _CUSTOM_SERIALIZERS.clear()
    _CUSTOM_SERIALIZERS.update(saved_serializers)


# --------------------------------------------------------------------------- #
# Closed-vocabulary additions                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "field_cls,expected_vocab_type",
    [
        (models.JSONField, "json"),
        (models.DurationField, "duration"),
        (models.GenericIPAddressField, "ip"),
        (models.BinaryField, "binary"),
        (models.FilePathField, "filepath"),
    ],
)
def test_field_type_for_new_builtin_types(field_cls, expected_vocab_type) -> None:
    field = field_cls()
    assert field_type_for(field) == expected_vocab_type


def test_field_type_for_unknown_type_is_unsupported() -> None:
    """A field whose internal_type isn't in the table → ``unsupported``."""

    class WeirdField(models.Field):
        def get_internal_type(self) -> str:
            return "WeirdField"

    assert field_type_for(WeirdField()) == "unsupported"


# --------------------------------------------------------------------------- #
# serialize_value round-trips for the new Python types                        #
# --------------------------------------------------------------------------- #
def test_serialize_timedelta() -> None:
    td = dt.timedelta(hours=2, minutes=30, seconds=15)
    assert serialize_value(td) == "2:30:15"


def test_serialize_bytes() -> None:
    raw = b"hello world"
    encoded = serialize_value(raw)
    assert encoded == base64.b64encode(raw).decode("ascii")
    # And it round-trips:
    assert base64.b64decode(encoded) == raw


def test_serialize_bytearray_and_memoryview() -> None:
    """BinaryField may surface bytearray/memoryview from some DBs."""
    raw = b"abc"
    assert serialize_value(bytearray(raw)) == base64.b64encode(raw).decode("ascii")
    assert serialize_value(memoryview(raw)) == base64.b64encode(raw).decode("ascii")


def test_serialize_list_recurses() -> None:
    """ArrayField returns a Python list; each element passes through."""
    today = dt.date(2025, 10, 5)
    out = serialize_value([1, "two", today, None])
    assert out == [1, "two", "2025-10-05", None]


def test_serialize_tuple_recurses() -> None:
    """Plain tuples (custom getters) serialize the same way as lists."""
    out = serialize_value((1, 2, 3))
    assert out == [1, 2, 3]


def test_serialize_dict_recurses() -> None:
    """JSONField returns a dict; values are recursively serialized."""
    today = dt.date(2025, 10, 5)
    payload = {"answer": 42, "today": today, "nested": [1, 2]}
    out = serialize_value(payload)
    assert out == {"answer": 42, "today": "2025-10-05", "nested": [1, 2]}


def test_serialize_dict_coerces_non_string_keys() -> None:
    """JSON object keys are strings; ints get coerced."""
    out = serialize_value({1: "one", 2: "two"})
    assert out == {"1": "one", "2": "two"}


def test_serialize_none_still_passes_through() -> None:
    """Regression guard — None must remain None, not ``"None"``."""
    assert serialize_value(None) is None


# --------------------------------------------------------------------------- #
# register_field_type extension hook                                          #
# --------------------------------------------------------------------------- #
def test_register_field_type_adds_to_vocabulary() -> None:
    register_field_type("FancyField", "fancy")

    class FancyField(models.Field):
        def get_internal_type(self) -> str:
            return "FancyField"

    assert field_type_for(FancyField()) == "fancy"


def test_register_field_type_custom_serializer_runs() -> None:
    """A registered serializer wins over the default dispatch."""
    register_field_type("MoneyField", "decimal", serializer=lambda v: f"${v}")

    class MoneyField(models.Field):
        def get_internal_type(self) -> str:
            return "MoneyField"

    out = serialize_value(42, field=MoneyField())
    assert out == "$42"


def test_register_field_type_silent_noop_on_builtin() -> None:
    """register_field_type must not override the closed vocabulary."""
    register_field_type("CharField", "evil", serializer=lambda v: "hijacked")

    field = models.CharField()
    # CharField is still string, not "evil"
    assert field_type_for(field) == "string"
    # And the default serializer still runs (no hijack)
    assert serialize_value("hello", field=field) == "hello"


def test_register_field_type_without_serializer_uses_default() -> None:
    """Registering only the vocab mapping → default serializer still runs."""
    register_field_type("PlainCustom", "string")

    class PlainCustom(models.Field):
        def get_internal_type(self) -> str:
            return "PlainCustom"

    out = serialize_value("hello", field=PlainCustom())
    assert out == "hello"


def test_field_argument_optional_for_back_compat() -> None:
    """Existing callers without a field reference must continue to work."""
    today = dt.date(2025, 1, 1)
    assert serialize_value(today) == "2025-01-01"
    assert serialize_value(None) is None
    assert serialize_value("abc") == "abc"
