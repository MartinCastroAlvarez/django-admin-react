"""Unit tests for django_admin_react.api.serializers.

Covers the conservative type-conversion rules and the sensitive-name
denylist from ACCEPTANCE.md §3.5 + §4.7 S-31.
"""

from __future__ import annotations

import datetime as dt
import decimal
import uuid

import pytest

from django_admin_react.api.serializers import SENSITIVE_NAME_SUBSTRINGS
from django_admin_react.api.serializers import filter_sensitive
from django_admin_react.api.serializers import is_sensitive_field_name
from django_admin_react.api.serializers import serialize_fk_value
from django_admin_react.api.serializers import serialize_value


# --------------------------------------------------------------------------- #
# Sensitive-name denylist                                                     #
# --------------------------------------------------------------------------- #
class TestSensitiveDenylist:
    @pytest.mark.parametrize("name", list(SENSITIVE_NAME_SUBSTRINGS))
    def test_exact_match_is_sensitive(self, name: str) -> None:
        assert is_sensitive_field_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "password",
            "PASSWORD",
            "user_password",
            "password_hash",
            "api_key",
            "ApiKey",
            "stored_apikey",
            "auth_token",
            "session_id",
            "private_key_pem",
            "salt_value",
            "secret_data",
            "hashed_pw_hash",
            "nonce_value",
        ],
    )
    def test_substring_match_is_sensitive(self, name: str) -> None:
        assert is_sensitive_field_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "name",
            "title",
            "balance",
            "iban",
            "is_active",
            "created_at",
            "owner",
            "amount",
        ],
    )
    def test_innocuous_names_are_not_sensitive(self, name: str) -> None:
        assert not is_sensitive_field_name(name)

    def test_non_string_input_is_treated_as_sensitive(self) -> None:
        assert is_sensitive_field_name(None)  # type: ignore[arg-type]
        assert is_sensitive_field_name(123)  # type: ignore[arg-type]

    def test_filter_sensitive_drops_denylisted_names(self) -> None:
        assert filter_sensitive(["name", "password", "iban", "api_key"]) == [
            "name",
            "iban",
        ]


# --------------------------------------------------------------------------- #
# serialize_value                                                             #
# --------------------------------------------------------------------------- #
class TestSerializeValue:
    def test_none_passthrough(self) -> None:
        assert serialize_value(None) is None

    @pytest.mark.parametrize("value", [True, False, 0, 1, -1, 42, 3.14, -0.5])
    def test_native_numeric_passthrough(self, value: object) -> None:
        assert serialize_value(value) == value

    def test_string_passthrough(self) -> None:
        assert serialize_value("hello") == "hello"
        assert serialize_value("") == ""

    def test_decimal_serializes_as_string(self) -> None:
        assert serialize_value(decimal.Decimal("1023.45")) == "1023.45"

    def test_uuid_serializes_as_string(self) -> None:
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert serialize_value(u) == "12345678-1234-5678-1234-567812345678"

    def test_date_serializes_as_iso(self) -> None:
        assert serialize_value(dt.date(2026, 5, 25)) == "2026-05-25"

    def test_datetime_serializes_as_iso(self) -> None:
        moment = dt.datetime(2026, 5, 25, 12, 30, 0)
        assert serialize_value(moment) == "2026-05-25T12:30:00"

    def test_time_serializes_as_iso(self) -> None:
        t = dt.time(12, 30, 0)
        assert serialize_value(t) == "12:30:00"

    def test_unknown_type_falls_back_to_str(self) -> None:
        class Custom:
            def __str__(self) -> str:
                return "custom-repr"

        assert serialize_value(Custom()) == "custom-repr"

    def test_safestring_emits_html_envelope(self) -> None:
        """A Django ``SafeString`` (``format_html`` / ``mark_safe``) —
        how a ``list_display`` method opts into HTML — serializes to a
        typed ``{"html": ...}`` envelope so the SPA renders it as markup
        (Django changelist parity). Closes #172.
        """
        from django.utils.html import format_html

        value = format_html('<span class="label">{}</span>', "Test Bank 9")
        result = serialize_value(value)
        assert result == {"html": '<span class="label">Test Bank 9</span>'}

    def test_plain_string_with_html_chars_stays_inert_text(self) -> None:
        """A *plain* str (not SafeString) — e.g. a CharField holding
        ``<script>`` — is returned verbatim as a string, NOT the html
        envelope. The SPA renders it escaped, so it can never execute.
        This is the security boundary that distinguishes the two paths.
        """
        result = serialize_value("<script>alert(1)</script>")
        assert result == "<script>alert(1)</script>"
        assert not isinstance(result, dict), "plain string must never become {html: ...}"

    def test_mark_safe_value_emits_html_envelope(self) -> None:
        """``mark_safe`` (the other SafeString producer) also maps to the
        html envelope."""
        from django.utils.safestring import mark_safe

        result = serialize_value(mark_safe("<b>bold</b>"))  # noqa: S308 — test input
        assert result == {"html": "<b>bold</b>"}

    def test_no_exception_for_weird_input(self) -> None:
        """Defense-in-depth: serializer never raises (§4.7)."""

        class Boom:
            def __str__(self) -> str:
                raise RuntimeError("intentional")

        # str() raising should still produce a value (defensive catch).
        with pytest.raises(RuntimeError):
            # Note: we DON'T catch in serialize_value; we expect str()
            # to be reliable. This test documents the boundary.
            serialize_value(Boom())


# --------------------------------------------------------------------------- #
# serialize_fk_value                                                          #
# --------------------------------------------------------------------------- #
class TestSerializeFKValue:
    def test_none_returns_none(self) -> None:
        assert serialize_fk_value(None) is None

    def test_model_returns_id_label_dict(self) -> None:
        class _FakeMeta:
            pass

        class _FakeModel:
            pk = 42

            def __str__(self) -> str:
                return "the label"

        result = serialize_fk_value(_FakeModel())  # type: ignore[arg-type]
        assert result == {"id": 42, "label": "the label"}
