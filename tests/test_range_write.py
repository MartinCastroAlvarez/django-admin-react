"""Unit tests for the range-field WRITE coercion (#238).

The symmetric half of #141 (the read envelope). The package never imports
``django.contrib.postgres`` / psycopg, so these exercise the coercion in
isolation — the field is detected by ``get_internal_type()`` (stubbed
here) and a psycopg ``Range`` is duck-typed, exactly as the production
code does.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from django_admin_react.api import writes
from django_admin_react.api.writes import _range_endpoints
from django_admin_react.api.writes import coerce_range_values


class _FakeRange:
    """psycopg ``Range``-shaped object (what the instance carries)."""

    def __init__(self, lower: Any, upper: Any, isempty: bool = False) -> None:
        self.lower = lower
        self.upper = upper
        self.isempty = isempty


# --------------------------------------------------------------------------- #
# _range_endpoints — every accepted input shape                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([1, 5], ("1", "5")),  # wire array
        ([None, 5], ("", "5")),  # unbounded lower
        ([1, None], ("1", "")),  # unbounded upper
        ({"value": {"lower": 1, "upper": 5}}, ("1", "5")),  # read envelope
        ({"lower": 1, "upper": 5}, ("1", "5")),  # bare object
        ({"value": None, "empty": True}, ("", "")),  # empty envelope
        (None, ("", "")),  # cleared
        ("garbage", ("", "")),  # unparseable → cleared, never crashes
    ],
)
def test_range_endpoints_shapes(value: Any, expected: tuple[str, str]) -> None:
    assert _range_endpoints(value) == expected


def test_range_endpoints_duck_typed_range_instance() -> None:
    assert _range_endpoints(_FakeRange(1, 5)) == ("1", "5")
    assert _range_endpoints(_FakeRange(None, 5)) == ("", "5")
    # An empty Range clears both endpoints.
    assert _range_endpoints(_FakeRange(1, 5, isempty=True)) == ("", "")


# --------------------------------------------------------------------------- #
# coerce_range_values — expands only range fields into _0 / _1                 #
# --------------------------------------------------------------------------- #
def test_coerce_range_values_expands_only_range_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    # Stub safe_get_field: "span" is a range field, everything else isn't.
    def fake_field(_model: Any, name: str) -> Any:
        if name == "span":
            return SimpleNamespace(get_internal_type=lambda: "IntegerRangeField")
        return SimpleNamespace(get_internal_type=lambda: "CharField")

    monkeypatch.setattr(writes, "safe_get_field", fake_field)

    form_data: dict[str, Any] = {"name": "x", "span": [1, 5]}
    out = coerce_range_values(form_data, model=object)  # type: ignore[arg-type]

    # The range field is split into the multi-widget keys; others untouched.
    assert out["span_0"] == "1"
    assert out["span_1"] == "5"
    assert "span" not in out
    assert out["name"] == "x"


def test_coerce_range_values_handles_instance_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """A PATCH that doesn't touch the field carries the instance's Range —
    it must still expand so the field isn't cleared."""
    monkeypatch.setattr(
        writes,
        "safe_get_field",
        lambda _m, name: SimpleNamespace(get_internal_type=lambda: "DateRangeField"),
    )
    out = coerce_range_values({"period": _FakeRange("2026-01-01", "2026-02-01")}, model=object)  # type: ignore[arg-type]
    assert out == {"period_0": "2026-01-01", "period_1": "2026-02-01"}


def test_coerce_range_values_missing_field_is_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(writes, "safe_get_field", lambda _m, _name: None)
    form_data = {"whatever": "value"}
    assert coerce_range_values(form_data, model=object) == {"whatever": "value"}  # type: ignore[arg-type]
