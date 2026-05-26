"""``GET /api/v1/schema/`` — OpenAPI 3.1 envelope schema.

Wire contract: ``docs/api-contract.md`` §7.

The schema describes the **envelope shapes** of every endpoint
(registry / list / detail / create / update / destroy / autocomplete /
actions / bulk / schema itself) plus the closed type vocabulary and
the error envelopes. It does **not** enumerate the consumer's models
— that would leak which models exist to a user who can't view them.
Per-model shape lives in ``GET /api/v1/<app>/<model>/`` (which is
permission-gated).

The schema is generated, not hand-written: ``_build_schema()`` walks
the closed type vocabulary in ``api/serializers.py`` to produce the
``components.schemas`` block. Anything documented in
``docs/api-contract.md`` is reflected here so a typed client like
``openapi-typescript`` produces a SPA-ready surface without
hand-translating Markdown.

The endpoint is staff-gated (same posture as the rest of the API)
so a public-facing site doesn't accidentally surface its API shape
to anyone. The schema reveals no row data and no model names — it
describes the contract shape — but keeping the gate consistent is
the simpler posture than introducing a "public" surface here.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import View

from django_admin_react.api.permissions import forbidden_response
from django_admin_react.api.permissions import is_admin_user
from django_admin_react.api.registry import get_admin_site
from django_admin_react.api.serializers import _CUSTOM_TYPE_BY_INTERNAL
from django_admin_react.api.serializers import _TYPE_BY_INTERNAL

OPENAPI_VERSION = "3.1.0"
SCHEMA_VERSION = "v1"


class SchemaView(View):
    """``GET /api/v1/schema/`` — return the OpenAPI 3.1 doc."""

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        admin_site = get_admin_site()
        if not is_admin_user(request, admin_site=admin_site):
            return forbidden_response(request)
        response = JsonResponse(_build_schema(), status=200)
        # The schema is static-shaped (doesn't reveal user-specific
        # data), but keeping no-store matches the rest of the API
        # posture and avoids "is this safe to cache?" confusion.
        response["Cache-Control"] = "no-store"
        return response


def _build_schema() -> dict[str, Any]:
    """Compose the OpenAPI doc from the closed contract surface."""
    return {
        "openapi": OPENAPI_VERSION,
        "info": {
            "title": "django-admin-react API",
            "version": SCHEMA_VERSION,
            "description": (
                "Wire contract between the React SPA and the Django "
                "backend. Endpoint shapes only — model registry and "
                "row data are returned by GET /api/v1/{app}/{model}/."
            ),
        },
        "components": _components(),
        "paths": _paths(),
    }


# --------------------------------------------------------------------------- #
# components.schemas — envelope shapes the contract uses everywhere           #
# --------------------------------------------------------------------------- #
def _components() -> dict[str, Any]:
    type_enum = sorted(
        {"foreignkey", "manytomany", "choice", "unsupported"}
        | set(_TYPE_BY_INTERNAL.values())
        | set(_CUSTOM_TYPE_BY_INTERNAL.values())
    )
    return {
        "schemas": {
            "Error": {
                "type": "object",
                "required": ["error"],
                "properties": {
                    "error": {
                        "type": "object",
                        "required": ["code", "message"],
                        "properties": {
                            "code": {
                                "type": "string",
                                "enum": [
                                    "bad_request",
                                    "validation_failed",
                                    "forbidden",
                                    "session_expired",
                                    "not_found",
                                    "method_not_allowed",
                                    "conflict",
                                    "internal_error",
                                ],
                            },
                            "message": {"type": "string"},
                            "fields": {
                                "type": "object",
                                "additionalProperties": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    }
                },
            },
            "FKEnvelope": {
                "type": "object",
                "required": ["id", "label"],
                "properties": {
                    "id": {},
                    "label": {"type": "string"},
                },
            },
            "FieldType": {"type": "string", "enum": type_enum},
            "Column": {
                "type": "object",
                "required": ["name", "label", "sortable", "editable"],
                "properties": {
                    "name": {"type": "string"},
                    "label": {"type": "string"},
                    "sortable": {"type": "boolean"},
                    "editable": {"type": "boolean"},
                },
            },
            "Filter": {
                "type": "object",
                "required": ["name", "label", "type"],
                "properties": {
                    "name": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["boolean", "choice", "foreignkey", "date", "custom"],
                    },
                    "choices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"value": {}, "label": {"type": "string"}},
                        },
                    },
                    "lookups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"value": {}, "label": {"type": "string"}},
                        },
                    },
                    "to": {
                        "type": "object",
                        "properties": {
                            "app_label": {"type": "string"},
                            "model_name": {"type": "string"},
                        },
                    },
                },
            },
            "ActionSpec": {
                "type": "object",
                "required": ["name", "label", "description", "requires_confirmation"],
                "properties": {
                    "name": {"type": "string"},
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                    "requires_confirmation": {"type": "boolean"},
                },
            },
            "DateHierarchy": {
                "type": "object",
                "required": ["field", "granularity_options", "active", "buckets"],
                "properties": {
                    "field": {"type": "string"},
                    "granularity_options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "active": {
                        "type": "object",
                        "properties": {
                            "year": {"type": ["integer", "null"]},
                            "month": {"type": ["integer", "null"]},
                            "day": {"type": ["integer", "null"]},
                        },
                    },
                    "buckets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["value", "count"],
                            "properties": {
                                "value": {"type": "integer"},
                                "count": {"type": "integer"},
                            },
                        },
                    },
                },
            },
            "ListResponse": {
                "type": "object",
                "required": [
                    "app_label",
                    "model_name",
                    "permissions",
                    "columns",
                    "search_fields",
                    "filters",
                    "actions",
                    "page",
                    "page_size",
                    "total",
                    "results",
                ],
                "properties": {
                    "app_label": {"type": "string"},
                    "model_name": {"type": "string"},
                    "permissions": {
                        "type": "object",
                        "properties": {
                            "view": {"type": "boolean"},
                            "add": {"type": "boolean"},
                            "change": {"type": "boolean"},
                            "delete": {"type": "boolean"},
                        },
                    },
                    "columns": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Column"},
                    },
                    "search_fields": {"type": "array", "items": {"type": "string"}},
                    "filters": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Filter"},
                    },
                    "actions": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/ActionSpec"},
                    },
                    "date_hierarchy": {
                        "$ref": "#/components/schemas/DateHierarchy"
                    },
                    "page": {"type": "integer"},
                    "page_size": {"type": "integer"},
                    "total": {"type": "integer"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["pk", "label", "fields"],
                            "properties": {
                                "pk": {},
                                "label": {"type": "string"},
                                "fields": {
                                    "type": "object",
                                    "additionalProperties": {},
                                },
                            },
                        },
                    },
                },
            },
            "FieldDescriptor": {
                "type": "object",
                "required": ["type", "label", "required", "readonly", "value"],
                "properties": {
                    "type": {"$ref": "#/components/schemas/FieldType"},
                    "label": {"type": "string"},
                    "required": {"type": "boolean"},
                    "readonly": {"type": "boolean"},
                    "help_text": {"type": "string"},
                    "value": {},
                    "to": {
                        "type": "object",
                        "properties": {
                            "app_label": {"type": "string"},
                            "model_name": {"type": "string"},
                        },
                    },
                    "max_length": {"type": "integer"},
                    "decimal_places": {"type": "integer"},
                    "choices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"value": {}, "label": {"type": "string"}},
                        },
                    },
                },
            },
            "DetailResponse": {
                "type": "object",
                "required": [
                    "app_label",
                    "model_name",
                    "pk",
                    "label",
                    "permissions",
                    "fieldsets",
                    "fields",
                ],
                "properties": {
                    "app_label": {"type": "string"},
                    "model_name": {"type": "string"},
                    "pk": {},
                    "label": {"type": "string"},
                    "permissions": {"type": "object"},
                    "fieldsets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": ["string", "null"]},
                                "fields": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "fields": {
                        "type": "object",
                        "additionalProperties": {
                            "$ref": "#/components/schemas/FieldDescriptor"
                        },
                    },
                },
            },
            "RegistryResponse": {
                "type": "object",
                "required": ["mount", "user", "apps"],
                "properties": {
                    "mount": {"type": "string"},
                    "user": {
                        "type": "object",
                        "properties": {
                            "id": {},
                            "username": {"type": "string"},
                            "display_name": {"type": "string"},
                            "is_staff": {"type": "boolean"},
                            "is_superuser": {"type": "boolean"},
                        },
                    },
                    "apps": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
        "responses": {
            "Error": {
                "description": "Error envelope.",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"}
                    }
                },
            }
        },
    }


# --------------------------------------------------------------------------- #
# paths — endpoint surface                                                    #
# --------------------------------------------------------------------------- #
def _paths() -> dict[str, Any]:
    return {
        "/api/v1/registry/": {
            "get": {
                "summary": "List models visible to the requesting user.",
                "responses": _ok_response("RegistryResponse"),
            },
        },
        "/api/v1/{app_label}/{model_name}/": {
            "get": {
                "summary": "List rows of one model.",
                "parameters": _list_params(),
                "responses": _ok_response("ListResponse"),
            },
            "post": {
                "summary": "Create one row.",
                "responses": {
                    "201": {"description": "Created."},
                    "400": {"$ref": "#/components/responses/Error"},
                    "403": {"$ref": "#/components/responses/Error"},
                },
            },
        },
        "/api/v1/{app_label}/{model_name}/{pk}/": {
            "get": {
                "summary": "Detail of one row.",
                "responses": _ok_response("DetailResponse"),
            },
            "patch": {
                "summary": "Partial update of one row.",
                "responses": _ok_response("DetailResponse"),
            },
            "delete": {
                "summary": "Delete one row.",
                "responses": {
                    "204": {"description": "Deleted."},
                    "403": {"$ref": "#/components/responses/Error"},
                    "404": {"$ref": "#/components/responses/Error"},
                },
            },
        },
        "/api/v1/{app_label}/{model_name}/autocomplete/": {
            "get": {
                "summary": "Typeahead picker for high-cardinality FK targets.",
                "responses": {
                    "200": {"description": "Autocomplete results + pagination."},
                    "400": {"$ref": "#/components/responses/Error"},
                },
            },
        },
        "/api/v1/{app_label}/{model_name}/actions/{action_name}/": {
            "post": {
                "summary": "Run a ModelAdmin.actions entry.",
                "responses": {
                    "200": {"description": "Executed."},
                    "404": {"$ref": "#/components/responses/Error"},
                },
            },
        },
        "/api/v1/{app_label}/{model_name}/bulk/": {
            "patch": {
                "summary": "Bulk PATCH multiple rows in one atomic transaction.",
                "responses": {
                    "200": {"description": "Per-row results + summary."},
                    "400": {"$ref": "#/components/responses/Error"},
                },
            },
        },
        "/api/v1/schema/": {
            "get": {
                "summary": "This endpoint — the OpenAPI 3.1 envelope schema.",
                "responses": {
                    "200": {"description": "OpenAPI 3.1 document."},
                },
            },
        },
    }


def _ok_response(schema_ref: str) -> dict[str, Any]:
    return {
        "200": {
            "description": "OK.",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{schema_ref}"}
                }
            },
        },
        "403": {"$ref": "#/components/responses/Error"},
        "404": {"$ref": "#/components/responses/Error"},
    }


def _list_params() -> list[dict[str, Any]]:
    return [
        {"name": "q", "in": "query", "schema": {"type": "string"}},
        {"name": "page", "in": "query", "schema": {"type": "integer"}},
        {"name": "page_size", "in": "query", "schema": {"type": "integer"}},
        {"name": "ordering", "in": "query", "schema": {"type": "string"}},
        {"name": "year", "in": "query", "schema": {"type": "integer"}},
        {"name": "month", "in": "query", "schema": {"type": "integer"}},
        {"name": "day", "in": "query", "schema": {"type": "integer"}},
    ]
