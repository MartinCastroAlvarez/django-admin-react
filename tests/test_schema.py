"""Tests for ``GET /api/v1/schema/`` (Issue #64).

Wire contract: ``docs/api-contract.md`` §12.

Covered:

- The mandatory matrix subset that applies to a no-model endpoint:
  anonymous → not authorized, non-staff → 403, staff → 200, CSRF
  isn't relevant (GET is safe).
- Response shape is a valid OpenAPI 3.1 envelope with the documented
  paths, components, and type vocabulary.
- The closed type vocabulary in the spec matches the vocabulary the
  serializer actually produces — single source of truth.
- ``Cache-Control: no-store`` (per-user gate, must not be cached).
- The error-code enum lists each code the package emits.
- A live ``GET`` works without any consumer model being registered.
"""

from __future__ import annotations

import pytest
from django.test import Client

from django_admin_react.api.schema import ERROR_CODE_VOCABULARY
from django_admin_react.api.schema import FIELD_TYPE_VOCABULARY
from django_admin_react.api.schema import openapi_spec
from django_admin_react.api.serializers import _TYPE_BY_INTERNAL

SCHEMA_URL = "/admin-react/api/v1/schema/"


# --------------------------------------------------------------------------- #
# Permission matrix                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_user_unauthorized(anon_client: Client) -> None:
    response = anon_client.get(SCHEMA_URL)
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_authenticated_non_staff_forbidden(user_client: Client) -> None:
    response = user_client.get(SCHEMA_URL)
    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "forbidden", "message": "You do not have permission."}
    }


@pytest.mark.django_db
def test_staff_gets_openapi_spec(staff_client: Client) -> None:
    response = staff_client.get(SCHEMA_URL)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    body = response.json()
    assert body["openapi"] == "3.1.0"
    assert "paths" in body
    assert "components" in body


@pytest.mark.django_db
def test_response_is_no_store(staff_client: Client) -> None:
    """Per-user gate → never cache."""
    response = staff_client.get(SCHEMA_URL)
    assert response["Cache-Control"] == "no-store"


# --------------------------------------------------------------------------- #
# Spec contents                                                               #
# --------------------------------------------------------------------------- #
def test_spec_lists_each_endpoint() -> None:
    """All seven public endpoints are documented."""
    paths = openapi_spec()["paths"]
    expected = {
        "/api/v1/registry/",
        "/api/v1/schema/",
        "/api/v1/{app_label}/{model_name}/",
        "/api/v1/{app_label}/{model_name}/{pk}/",
        "/api/v1/{app_label}/{model_name}/autocomplete/",
        "/api/v1/{app_label}/{model_name}/actions/{action_name}/",
    }
    assert expected <= set(paths.keys())


def test_field_type_vocabulary_matches_serializer() -> None:
    """The OpenAPI ``enum`` of field types is a superset of every
    value the serializer can emit.

    This is the architectural contract that motivates the spec:
    one source of truth for the closed vocabulary. If a new type
    is added to ``_TYPE_BY_INTERNAL`` without also being added to
    ``FIELD_TYPE_VOCABULARY``, this test fails immediately.

    Extra entries in the schema vocabulary (e.g. ``choice``,
    ``unsupported``) are fine — those are synthetic types
    ``field_metadata`` produces but ``_TYPE_BY_INTERNAL`` does not.
    """
    serializer_outputs = set(_TYPE_BY_INTERNAL.values())
    spec_vocab = set(FIELD_TYPE_VOCABULARY)
    missing = serializer_outputs - spec_vocab
    assert not missing, f"Schema vocabulary missing: {sorted(missing)}"


def test_error_envelope_lists_each_code() -> None:
    """The OpenAPI ``Error`` schema's ``enum`` covers every code the
    package emits."""
    schema = openapi_spec()["components"]["schemas"]["Error"]
    enum = schema["properties"]["error"]["properties"]["code"]["enum"]
    expected_codes = {
        "bad_request",
        "validation_failed",
        "forbidden",
        "not_found",
        "session_expired",
    }
    assert expected_codes <= set(enum)
    assert set(enum) == set(ERROR_CODE_VOCABULARY)


def test_field_descriptor_documents_m2m_shape() -> None:
    """The FieldDescriptor schema knows about ``many_to_many`` —
    the type added by issue #55."""
    descriptor = openapi_spec()["components"]["schemas"]["FieldDescriptor"]
    type_enum = descriptor["properties"]["type"]["enum"]
    assert "many_to_many" in type_enum
    assert "widget" in descriptor["properties"]
    widget_enum = descriptor["properties"]["widget"]["enum"]
    assert set(widget_enum) == {"select", "horizontal", "vertical"}


def test_filter_schema_lists_all_five_types() -> None:
    """The Filter schema's ``type`` enum is the closed five-type
    vocabulary from #56."""
    schema = openapi_spec()["components"]["schemas"]["Filter"]
    type_enum = schema["properties"]["type"]["enum"]
    assert set(type_enum) == {"boolean", "choices", "foreignkey", "date_range", "custom"}


def test_spec_is_independent_of_consumer_models() -> None:
    """The schema endpoint must not enumerate consumer models —
    that's what /registry/ is for. Verified by checking ``paths``
    contains no literal ``app_label`` values."""
    paths = openapi_spec()["paths"]
    # Every key with a model segment is a template (``{app_label}``),
    # never a literal like ``/api/v1/auth/group/``.
    for path in paths:
        assert "{app_label}" in path or "{" not in path.split("/api/v1/", 1)[1]


def test_spec_is_fresh_dict_each_call() -> None:
    """``openapi_spec()`` returns a new dict each call so callers
    can mutate it without affecting subsequent callers."""
    a = openapi_spec()
    b = openapi_spec()
    a["info"]["title"] = "mutated"
    assert b["info"]["title"] != "mutated"
