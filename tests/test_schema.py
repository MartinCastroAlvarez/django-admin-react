"""Tests for ``GET /api/v1/schema/`` (Issue #64).

The schema endpoint surfaces the OpenAPI 3.1 doc for the envelope
shapes. It is **not** model-introspecting (the per-model shapes live
on the model-list endpoint, which is permission-gated).
"""

from __future__ import annotations

import pytest
from django.test import Client

SCHEMA_URL = "/admin-react/api/v1/schema/"


# --------------------------------------------------------------------------- #
# Permission matrix                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_anonymous_unauthorized(anon_client: Client) -> None:
    response = anon_client.get(SCHEMA_URL)
    assert response.status_code == 403


@pytest.mark.django_db
def test_non_staff_forbidden(user_client: Client) -> None:
    response = user_client.get(SCHEMA_URL)
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Shape                                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
def test_schema_is_openapi_31(superuser_client: Client) -> None:
    response = superuser_client.get(SCHEMA_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["openapi"] == "3.1.0"


@pytest.mark.django_db
def test_schema_has_known_paths(superuser_client: Client) -> None:
    body = superuser_client.get(SCHEMA_URL).json()
    paths = body["paths"]
    expected = {
        "/api/v1/registry/",
        "/api/v1/{app_label}/{model_name}/",
        "/api/v1/{app_label}/{model_name}/{pk}/",
        "/api/v1/{app_label}/{model_name}/autocomplete/",
        "/api/v1/{app_label}/{model_name}/actions/{action_name}/",
        "/api/v1/{app_label}/{model_name}/bulk/",
        "/api/v1/schema/",
    }
    assert expected.issubset(set(paths.keys()))


@pytest.mark.django_db
def test_schema_components_include_known_shapes(superuser_client: Client) -> None:
    body = superuser_client.get(SCHEMA_URL).json()
    schemas = body["components"]["schemas"]
    for required in (
        "Error",
        "FKEnvelope",
        "FieldType",
        "Column",
        "Filter",
        "ActionSpec",
        "DateHierarchy",
        "ListResponse",
        "FieldDescriptor",
        "DetailResponse",
        "RegistryResponse",
    ):
        assert required in schemas, f"{required} missing from components.schemas"


@pytest.mark.django_db
def test_field_type_enum_includes_manytomany_and_json(
    superuser_client: Client,
) -> None:
    """The closed type vocabulary surfaces here too — guards drift."""
    body = superuser_client.get(SCHEMA_URL).json()
    enum = body["components"]["schemas"]["FieldType"]["enum"]
    assert "manytomany" in enum
    assert "json" in enum
    assert "boolean" in enum
    assert "foreignkey" in enum


@pytest.mark.django_db
def test_error_codes_include_session_expired(superuser_client: Client) -> None:
    """Session expiry (#63) is one of the error envelope codes."""
    body = superuser_client.get(SCHEMA_URL).json()
    error_schema = body["components"]["schemas"]["Error"]
    codes = error_schema["properties"]["error"]["properties"]["code"]["enum"]
    assert "forbidden" in codes
    assert "session_expired" in codes
    assert "validation_failed" in codes


@pytest.mark.django_db
def test_schema_does_not_enumerate_models(superuser_client: Client) -> None:
    """The schema describes envelope shapes — it must not list models."""
    body = superuser_client.get(SCHEMA_URL).json()
    # No path enumerates a concrete app/model.
    for path in body["paths"]:
        assert "{app_label}" in path or path in (
            "/api/v1/registry/",
            "/api/v1/schema/",
        )


@pytest.mark.django_db
def test_cache_control_no_store(superuser_client: Client) -> None:
    response = superuser_client.get(SCHEMA_URL)
    assert response["Cache-Control"] == "no-store"
