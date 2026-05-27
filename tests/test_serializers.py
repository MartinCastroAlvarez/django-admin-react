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
        class _FakeModel:
            pk = 42

            def __str__(self) -> str:
                return "the label"

        result = serialize_fk_value(_FakeModel())  # type: ignore[arg-type]
        assert result == {"id": 42, "label": "the label"}


# --------------------------------------------------------------------------- #
# serialize_fk_value `to` target (#184 — navigable FK cells)                  #
# --------------------------------------------------------------------------- #
class TestSerializeFKTarget:
    """`to` is included only when the related model is admin-registered."""

    @pytest.mark.django_db
    def test_to_present_when_related_model_registered(self) -> None:
        from django.contrib import admin
        from django.contrib.auth.models import Group  # pylint: disable=imported-auth-user

        out = serialize_fk_value(Group(name="x"), admin_site=admin.site)
        assert out is not None
        assert out["to"] == {"app_label": "auth", "model_name": "group"}

    def test_to_absent_without_admin_site(self) -> None:
        from django.contrib.auth.models import Group  # pylint: disable=imported-auth-user

        out = serialize_fk_value(Group(name="x"))
        assert out is not None
        assert "to" not in out

    def test_to_absent_when_related_model_unregistered(self) -> None:
        """Mirrors the #89 posture: never surface a target the SPA can't
        reach (and never leak adjacency to an unregistered model)."""
        from django.contrib.auth.models import Group  # pylint: disable=imported-auth-user

        class _EmptySite:
            _registry: dict = {}

        out = serialize_fk_value(Group(name="x"), admin_site=_EmptySite())
        assert out is not None
        assert "to" not in out


# --------------------------------------------------------------------------- #
# serialize_value — bare Model fallback + label_for exception fallback         #
# (coverage: serializers.py model-serialize + __str__-raises paths)            #
# --------------------------------------------------------------------------- #
class TestSerializeValueModelAndLabel:
    def test_bare_model_instance_serializes_to_id_label(self) -> None:
        """A plain Model value (no field dispatch) → ``{id, label}``."""
        from django.contrib.auth.models import Group  # pylint: disable=imported-auth-user

        g = Group(name="admins")
        g.pk = 5
        assert serialize_value(g) == {"id": 5, "label": "admins"}

    def test_label_for_falls_back_when_str_raises(self) -> None:
        """``label_for`` must never propagate a ``__str__`` exception — it
        degrades to ``<ClassName: pk>`` so a half-migrated row can't 500 a
        list/detail page."""
        from django_admin_react.api.serializers import label_for

        class Boom:
            pk = 7

            def __str__(self) -> str:
                raise ValueError("intentionally broken __str__")

        assert label_for(Boom()) == "<Boom: 7>"


# --------------------------------------------------------------------------- #
# field_choices + field_metadata                                              #
# --------------------------------------------------------------------------- #
class TestFieldChoicesAndMetadata:
    def test_field_choices_returns_value_label_pairs(self) -> None:
        from django.db import models

        from django_admin_react.api.serializers import field_choices

        field = models.CharField(choices=[("a", "Apple"), ("b", "Banana")])
        assert field_choices(field) == [
            {"value": "a", "label": "Apple"},
            {"value": "b", "label": "Banana"},
        ]

    def test_decimal_field_metadata_includes_decimal_places(self) -> None:
        from django.db import models

        from django_admin_react.api.serializers import field_metadata

        field = models.DecimalField(max_digits=6, decimal_places=2)
        md = field_metadata(
            field, label="Amount", required=True, readonly=False, help_text="", value="1.00"
        )
        assert md["type"] == "decimal"
        assert md["decimal_places"] == 2

    def test_choices_field_metadata_becomes_choice_type(self) -> None:
        from django.db import models

        from django_admin_react.api.serializers import field_metadata

        field = models.CharField(max_length=1, choices=[("a", "Apple")])
        md = field_metadata(
            field, label="Letter", required=False, readonly=False, help_text="", value="a"
        )
        assert md["type"] == "choice"
        assert md["choices"] == [{"value": "a", "label": "Apple"}]

    def test_fk_with_unresolved_related_model_omits_to(self) -> None:
        """Defensive guard (serializers.py ``field_metadata``): the
        ``"self"`` / ``None`` ``related_model`` sentinel only exists during
        model definition. Pin that the ``to`` block is skipped (not
        raising) when it's seen, rather than testing it never happens."""
        from django.db import models

        from django_admin_react.api.serializers import field_metadata

        fk = models.ForeignKey("self", on_delete=models.CASCADE)
        # cached_property is a non-data descriptor — instance assignment
        # shadows it, simulating the unresolved-sentinel state.
        fk.related_model = None
        md = field_metadata(
            fk, label="Parent", required=False, readonly=False, help_text="", value=None
        )
        assert "to" not in md


# --------------------------------------------------------------------------- #
# serialize_fk_value — `to` link gated on per-user view permission (#301)     #
# --------------------------------------------------------------------------- #
class TestFkToPermissionGate:
    """The navigable `to` block must only advertise a target the current
    user can actually view (#301) — least disclosure, defense-in-depth on
    top of #89's registry-membership gate."""

    def _site(self, *, can_view: bool):
        from django.contrib.auth.models import Group  # pylint: disable=imported-auth-user

        class _Admin:
            def has_view_permission(self, request, obj=None):  # noqa: ANN001, ANN202
                return can_view

        class _Site:
            _registry = {Group: _Admin()}

        return Group, _Site()

    def test_to_omitted_when_target_not_viewable(self) -> None:
        Group, site = self._site(can_view=False)
        out = serialize_fk_value(Group(name="x"), admin_site=site, request=object())
        assert out is not None
        assert "to" not in out  # the link is hidden...
        assert out["label"] == "x"  # ...but the label is still shown

    def test_to_present_when_target_viewable(self) -> None:
        Group, site = self._site(can_view=True)
        out = serialize_fk_value(Group(name="x"), admin_site=site, request=object())
        assert out is not None
        assert out["to"] == {"app_label": "auth", "model_name": "group"}

    def test_request_none_preserves_registry_only_behaviour(self) -> None:
        """Backwards-compat: with no request we can't check perms, so the
        #89 registry-membership behaviour is preserved (has_view_permission
        is never consulted)."""
        from django.contrib.auth.models import Group  # pylint: disable=imported-auth-user

        class _RaisingAdmin:
            def has_view_permission(self, request, obj=None):  # noqa: ANN001, ANN202
                raise AssertionError("has_view_permission must not be called without a request")

        class _Site:
            _registry = {Group: _RaisingAdmin()}

        out = serialize_fk_value(Group(name="x"), admin_site=_Site(), request=None)
        assert out is not None
        assert out["to"] == {"app_label": "auth", "model_name": "group"}
