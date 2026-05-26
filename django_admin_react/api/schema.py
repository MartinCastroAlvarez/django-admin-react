"""Machine-readable OpenAPI 3.1 spec for the JSON API (issue #64).

The spec describes the package's **stable wire shapes** — registry,
list, detail, write, error envelopes, and the closed type vocabulary
— without enumerating the consumer's models. The registry endpoint
(``/api/v1/registry/``) already does per-user model enumeration; this
schema describes the *shapes* those endpoints speak, not the model
catalog.

Why a programmatic spec instead of a generator:

- The package's wire contract is intentionally tight (closed
  vocabularies; defense-in-depth). Hand-curated OpenAPI guarantees
  the spec matches the documented contract exactly — there is no
  drift between a generator's guesses and the actual response shape.
- Consumers can run the spec through any OpenAPI tool (typed client
  generation, response validation in their own tests, contract
  drift detection).
- The spec is small enough to live in one file. Splitting per-tag
  would just add file-juggling without any payoff at this size.

Out of scope for v1:

- Listing consumer models in `paths` (the registry endpoint covers
  that, per-user). The schema documents the *shape* of those
  endpoints, not the catalog.
- Per-filter-type sub-schemas (the §11 ``filters[]`` array is typed
  as a discriminated union conceptually; we surface the union but
  keep the inner properties open-additional rather than locked, so
  the contract can extend without breaking generators).
"""

from __future__ import annotations

from typing import Any
from typing import Final

# Closed vocabulary the SPA knows how to render. Mirrors
# ``serializers._TYPE_BY_INTERNAL`` outputs plus the synthetic
# ``choice`` / ``unsupported`` values produced by ``field_metadata``.
# Single source of truth here so the OpenAPI ``enum`` is the same
# closed list the SPA actually branches on.
FIELD_TYPE_VOCABULARY: Final[tuple[str, ...]] = (
    "array",
    "binary",
    "boolean",
    "choice",
    "date",
    "datetime",
    "decimal",
    "duration",
    "email",
    "filepath",
    "float",
    "foreignkey",
    "integer",
    "ip",
    "json",
    "many_to_many",
    "range",
    "slug",
    "string",
    "text",
    "time",
    "unsupported",
    "url",
    "uuid",
)

ERROR_CODE_VOCABULARY: Final[tuple[str, ...]] = (
    "bad_request",
    "validation_failed",
    "not_authenticated",
    "session_expired",
    "forbidden",
    "not_found",
    "method_not_allowed",
    "conflict",
)


def openapi_spec() -> dict[str, Any]:
    """Return the OpenAPI 3.1 spec for the JSON API.

    Returns a fresh dict each call (cheap — the spec is ~12KB of
    Python literals) so callers can mutate the result without
    affecting subsequent calls. The endpoint view is responsible for
    serializing to JSON and setting cache headers.
    """
    return {
        "openapi": "3.1.0",
        "info": _info(),
        "tags": _tags(),
        "paths": _paths(),
        "components": {
            "schemas": _schemas(),
            "responses": _responses(),
            "parameters": _parameters(),
        },
    }


# --------------------------------------------------------------------------- #
# Top-level metadata                                                          #
# --------------------------------------------------------------------------- #
def _info() -> dict[str, Any]:
    """``info`` block — version is decoupled from the package version on
    purpose; the **wire contract** version moves only when the wire
    shape changes (additive bumps for new fields, breaking bumps for
    any non-additive change)."""
    return {
        "title": "django-admin-react JSON API",
        "version": "1.0.0",
        "summary": (
            "Wire-shape contract for the django-admin-react JSON API. "
            "Per-user model enumeration lives at /api/v1/registry/; this "
            "spec describes the shapes those endpoints speak."
        ),
        "description": (
            "All endpoints require an authenticated staff session and a "
            "CSRF token on unsafe methods. The full prose contract is in "
            "docs/api-contract.md; this OpenAPI doc is the "
            "machine-readable mirror."
        ),
        "license": {"name": "MIT"},
    }


def _tags() -> list[dict[str, Any]]:
    """Endpoint groups, in the order the contract presents them."""
    return [
        {"name": "registry", "description": "Per-user model catalog."},
        {"name": "list", "description": "Paginated row listing."},
        {"name": "detail", "description": "Single-row read."},
        {"name": "write", "description": "Create / update / delete."},
        {"name": "actions", "description": "ModelAdmin bulk actions."},
        {"name": "autocomplete", "description": "FK picker search."},
        {"name": "schema", "description": "This document."},
    ]


# --------------------------------------------------------------------------- #
# Paths                                                                       #
# --------------------------------------------------------------------------- #
def _paths() -> dict[str, Any]:
    """The path table.

    Path template variables match the URLconf — ``{app_label}`` and
    ``{model_name}`` are the consumer's model identifiers; ``{pk}``
    is the row primary key. The schema never tries to enumerate
    consumer models — those live in the registry response.
    """
    return {
        "/api/v1/registry/": {
            "get": _op_registry(),
        },
        "/api/v1/schema/": {
            "get": _op_schema(),
        },
        "/api/v1/{app_label}/{model_name}/": {
            "parameters": [_ref("parameters", "AppLabel"), _ref("parameters", "ModelName")],
            "get": _op_list(),
            "post": _op_create(),
        },
        "/api/v1/{app_label}/{model_name}/{pk}/": {
            "parameters": [
                _ref("parameters", "AppLabel"),
                _ref("parameters", "ModelName"),
                _ref("parameters", "Pk"),
            ],
            "get": _op_detail(),
            "patch": _op_update(),
            "delete": _op_destroy(),
        },
        "/api/v1/{app_label}/{model_name}/autocomplete/": {
            "parameters": [_ref("parameters", "AppLabel"), _ref("parameters", "ModelName")],
            "get": _op_autocomplete(),
        },
        "/api/v1/{app_label}/{model_name}/actions/{action_name}/": {
            "parameters": [
                _ref("parameters", "AppLabel"),
                _ref("parameters", "ModelName"),
                {
                    "name": "action_name",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                },
            ],
            "post": _op_action(),
        },
    }


def _op_registry() -> dict[str, Any]:
    return {
        "tags": ["registry"],
        "summary": "List apps/models the user can see.",
        "responses": {
            "200": {
                "description": "Registry payload.",
                "content": {"application/json": {"schema": _ref("schemas", "Registry")}},
            },
            "403": _ref("responses", "Forbidden"),
        },
    }


def _op_schema() -> dict[str, Any]:
    return {
        "tags": ["schema"],
        "summary": "This OpenAPI 3.1 document.",
        "responses": {
            "200": {
                "description": "The OpenAPI 3.1 spec for this API.",
                "content": {"application/json": {"schema": {"type": "object"}}},
            },
            "403": _ref("responses", "Forbidden"),
        },
    }


def _op_list() -> dict[str, Any]:
    return {
        "tags": ["list"],
        "summary": "Paginated list of rows for one model.",
        "parameters": [
            {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Search."},
            {
                "name": "page",
                "in": "query",
                "schema": {"type": "integer", "minimum": 1, "default": 1},
            },
            {"name": "page_size", "in": "query", "schema": {"type": "integer", "minimum": 1}},
            {"name": "ordering", "in": "query", "schema": {"type": "string"}},
        ],
        "responses": {
            "200": {
                "description": "List payload.",
                "content": {"application/json": {"schema": _ref("schemas", "ListResponse")}},
            },
            "403": _ref("responses", "Forbidden"),
            "404": _ref("responses", "NotFound"),
        },
    }


def _op_detail() -> dict[str, Any]:
    return {
        "tags": ["detail"],
        "summary": "Read one row.",
        "responses": {
            "200": {
                "description": "Detail payload.",
                "content": {"application/json": {"schema": _ref("schemas", "DetailResponse")}},
            },
            "403": _ref("responses", "Forbidden"),
            "404": _ref("responses", "NotFound"),
        },
    }


def _op_create() -> dict[str, Any]:
    return {
        "tags": ["write"],
        "summary": "Create a new row.",
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _ref("schemas", "WritePayload")}},
        },
        "responses": {
            "201": {
                "description": "Created.",
                "content": {"application/json": {"schema": _ref("schemas", "CreateResponse")}},
            },
            "400": _ref("responses", "BadRequest"),
            "403": _ref("responses", "Forbidden"),
            "404": _ref("responses", "NotFound"),
        },
    }


def _op_update() -> dict[str, Any]:
    return {
        "tags": ["write"],
        "summary": "Partially update a row.",
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _ref("schemas", "WritePayload")}},
        },
        "responses": {
            "200": {
                "description": "Updated; full detail payload returned.",
                "content": {"application/json": {"schema": _ref("schemas", "DetailResponse")}},
            },
            "400": _ref("responses", "BadRequest"),
            "403": _ref("responses", "Forbidden"),
            "404": _ref("responses", "NotFound"),
        },
    }


def _op_destroy() -> dict[str, Any]:
    return {
        "tags": ["write"],
        "summary": "Delete a row.",
        "responses": {
            "204": {"description": "Deleted; no body."},
            "403": _ref("responses", "Forbidden"),
            "404": _ref("responses", "NotFound"),
        },
    }


def _op_autocomplete() -> dict[str, Any]:
    return {
        "tags": ["autocomplete"],
        "summary": "FK picker — search rows of the target model.",
        "parameters": [
            {"name": "q", "in": "query", "schema": {"type": "string"}},
            {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}},
        ],
        "responses": {
            "200": {
                "description": "Autocomplete results.",
                "content": {
                    "application/json": {"schema": _ref("schemas", "AutocompleteResponse")}
                },
            },
            "403": _ref("responses", "Forbidden"),
            "404": _ref("responses", "NotFound"),
        },
    }


def _op_action() -> dict[str, Any]:
    return {
        "tags": ["actions"],
        "summary": "Run a ModelAdmin action across selected rows.",
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": _ref("schemas", "ActionPayload")}},
        },
        "responses": {
            "200": {
                "description": "Action ran.",
                "content": {"application/json": {"schema": _ref("schemas", "ActionResponse")}},
            },
            "400": _ref("responses", "BadRequest"),
            "403": _ref("responses", "Forbidden"),
            "404": _ref("responses", "NotFound"),
        },
    }


# --------------------------------------------------------------------------- #
# Components — schemas                                                        #
# --------------------------------------------------------------------------- #
def _schemas() -> dict[str, Any]:
    return {
        "Error": _error_schema(),
        "Permissions": {
            "type": "object",
            "required": ["view", "add", "change", "delete"],
            "properties": {
                "view": {"type": "boolean"},
                "add": {"type": "boolean"},
                "change": {"type": "boolean"},
                "delete": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "ModelRef": {
            "type": "object",
            "required": ["app_label", "model_name"],
            "properties": {
                "app_label": {"type": "string"},
                "model_name": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "FKValue": {
            "type": ["object", "null"],
            "required": ["id", "label"],
            "properties": {
                "id": {"type": ["integer", "string"]},
                "label": {"type": "string"},
            },
        },
        "M2MItem": {
            "type": "object",
            "required": ["id", "label"],
            "properties": {
                "id": {"type": ["integer", "string"]},
                "label": {"type": "string"},
            },
        },
        "Registry": _registry_schema(),
        "ListResponse": _list_schema(),
        "DetailResponse": _detail_schema(),
        "WritePayload": _write_payload_schema(),
        "CreateResponse": {
            "type": "object",
            "required": ["pk", "label", "redirect"],
            "properties": {
                "pk": {"type": ["integer", "string"]},
                "label": {"type": "string"},
                "redirect": {"type": "string"},
            },
        },
        "AutocompleteResponse": {
            "type": "object",
            "required": ["results", "pagination"],
            "properties": {
                "results": {
                    "type": "array",
                    "items": _ref("schemas", "M2MItem"),
                },
                "pagination": {
                    "type": "object",
                    "properties": {
                        "has_more": {"type": "boolean"},
                        "page": {"type": "integer"},
                    },
                },
            },
        },
        "ActionPayload": {
            "type": "object",
            "required": ["pks"],
            "properties": {
                "pks": {"type": "array", "items": {"type": ["integer", "string"]}},
                "confirmed": {"type": "boolean", "default": False},
            },
        },
        "ActionResponse": {
            "type": "object",
            "properties": {
                "ran": {"type": "boolean"},
                "count": {"type": "integer"},
                "message": {"type": "string"},
            },
        },
        "FieldDescriptor": _field_descriptor_schema(),
        "Filter": _filter_schema(),
        "DateHierarchy": _date_hierarchy_schema(),
    }


def _error_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "string", "enum": list(ERROR_CODE_VOCABULARY)},
                    "message": {"type": "string"},
                    "fields": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "description": ("Populated only when code == 'validation_failed'."),
                    },
                },
            },
        },
    }


def _registry_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["mount", "user", "apps"],
        "properties": {
            "mount": {"type": "string"},
            "user": {
                "type": "object",
                "required": ["id", "username", "is_staff", "is_superuser"],
                "properties": {
                    "id": {"type": ["integer", "string"]},
                    "username": {"type": "string"},
                    "is_staff": {"type": "boolean"},
                    "is_superuser": {"type": "boolean"},
                    "display_name": {"type": "string"},
                },
            },
            "apps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["app_label", "models"],
                    "properties": {
                        "app_label": {"type": "string"},
                        "verbose_name": {"type": "string"},
                        "models": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["app_label", "model_name", "permissions"],
                                "properties": {
                                    "app_label": {"type": "string"},
                                    "model_name": {"type": "string"},
                                    "verbose_name": {"type": "string"},
                                    "verbose_name_plural": {"type": "string"},
                                    "object_name": {"type": "string"},
                                    "permissions": _ref("schemas", "Permissions"),
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def _list_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "app_label",
            "model_name",
            "permissions",
            "columns",
            "search_fields",
            "page",
            "page_size",
            "total",
            "results",
        ],
        "properties": {
            "app_label": {"type": "string"},
            "model_name": {"type": "string"},
            "permissions": _ref("schemas", "Permissions"),
            "columns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "label", "sortable"],
                    "properties": {
                        "name": {"type": "string"},
                        "label": {"type": "string"},
                        "sortable": {"type": "boolean"},
                    },
                },
            },
            "search_fields": {"type": "array", "items": {"type": "string"}},
            "filters": {"type": "array", "items": _ref("schemas", "Filter")},
            "date_hierarchy": _ref("schemas", "DateHierarchy"),
            "page": {"type": "integer", "minimum": 1},
            "page_size": {"type": "integer", "minimum": 1},
            "total": {"type": "integer", "minimum": 0},
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["pk", "label", "fields"],
                    "properties": {
                        "pk": {"type": ["integer", "string"]},
                        "label": {"type": "string"},
                        "fields": {"type": "object", "additionalProperties": True},
                    },
                },
            },
        },
    }


def _detail_schema() -> dict[str, Any]:
    return {
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
            "pk": {"type": ["integer", "string"]},
            "label": {"type": "string"},
            "permissions": _ref("schemas", "Permissions"),
            "fieldsets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["fields"],
                    "properties": {
                        "title": {"type": ["string", "null"]},
                        "fields": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "fields": {
                "type": "object",
                "additionalProperties": _ref("schemas", "FieldDescriptor"),
            },
        },
    }


def _field_descriptor_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["type", "label", "required", "readonly"],
        "properties": {
            "type": {"type": "string", "enum": list(FIELD_TYPE_VOCABULARY)},
            "label": {"type": "string"},
            "required": {"type": "boolean"},
            "readonly": {"type": "boolean"},
            "help_text": {"type": "string"},
            "value": {
                "description": (
                    "Shape depends on `type`: scalar for boolean/numeric/string, "
                    "object for foreignkey, list of {id,label} for many_to_many, "
                    "etc. See docs/api-contract.md §4."
                ),
            },
            "max_length": {"type": "integer"},
            "decimal_places": {"type": "integer"},
            "choices": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "value": {},
                        "label": {"type": "string"},
                    },
                },
            },
            "to": _ref("schemas", "ModelRef"),
            "through": {"oneOf": [_ref("schemas", "ModelRef"), {"type": "null"}]},
            "widget": {"type": "string", "enum": ["select", "horizontal", "vertical"]},
        },
        "additionalProperties": True,
    }


def _filter_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["type", "name", "label"],
        "properties": {
            "type": {
                "type": "string",
                "enum": ["boolean", "choices", "foreignkey", "date_range", "custom"],
            },
            "name": {"type": "string"},
            "label": {"type": "string"},
            "choices": {"type": "array"},
            "lookups": {"type": "array"},
            "to": _ref("schemas", "ModelRef"),
        },
    }


def _date_hierarchy_schema() -> dict[str, Any]:
    return {
        "type": ["object", "null"],
        "properties": {
            "field": {"type": "string"},
            "granularity_options": {"type": "array", "items": {"type": "string"}},
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
    }


def _write_payload_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "description": (
            "Per-field write keys. Keys must be in the writable set "
            "returned by the corresponding GET detail. Unknown / "
            "readonly / excluded / sensitive-named keys return 400."
        ),
        "additionalProperties": True,
    }


# --------------------------------------------------------------------------- #
# Components — responses + parameters                                         #
# --------------------------------------------------------------------------- #
def _responses() -> dict[str, Any]:
    return {
        "BadRequest": {
            "description": "Malformed payload, unknown keys, or validation failure.",
            "content": {"application/json": {"schema": _ref("schemas", "Error")}},
        },
        "Forbidden": {
            "description": "Not authenticated as staff, missing permission, or CSRF.",
            "content": {"application/json": {"schema": _ref("schemas", "Error")}},
        },
        "NotFound": {
            "description": "Unregistered model, or row not visible to this user.",
            "content": {"application/json": {"schema": _ref("schemas", "Error")}},
        },
    }


def _parameters() -> dict[str, Any]:
    return {
        "AppLabel": {
            "name": "app_label",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        },
        "ModelName": {
            "name": "model_name",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        },
        "Pk": {
            "name": "pk",
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
            "description": "Primary key, serialized as a string.",
        },
    }


def _ref(category: str, name: str) -> dict[str, str]:
    """Build an OpenAPI ``$ref`` pointer at ``#/components/<category>/<name>``."""
    return {"$ref": f"#/components/{category}/{name}"}
