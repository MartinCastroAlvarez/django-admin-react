# API contract (v1)

This document defines the stable contract between the Django backend and
the React frontend. **Changes to this contract require a PR that updates
this file in lockstep**, plus matching changes on both sides.

- API base path: whatever the consumer mounts. All examples below use
  `/admin-react/api/v1/` for clarity.
- Auth: Django session cookie. Unsafe methods require the
  `X-CSRFToken` header.
- Encoding: `application/json` request and response bodies.
- Timezones: all datetimes are ISO 8601 with offset (UTC unless the
  consumer's `USE_TZ` is False).
- Errors: see §6 below.

---

## 1. Endpoint summary

| Method | Path                                                | Purpose                          | Auth         |
| ------ | --------------------------------------------------- | -------------------------------- | ------------ |
| GET    | `/api/v1/registry/`                                 | List apps/models the user sees   | staff        |
| GET    | `/api/v1/{app_label}/{model_name}/`                 | List objects                     | staff + view |
| POST   | `/api/v1/{app_label}/{model_name}/`                 | Create an object                 | staff + add  |
| GET    | `/api/v1/{app_label}/{model_name}/{pk}/`            | Object detail                    | staff + view |
| PATCH  | `/api/v1/{app_label}/{model_name}/{pk}/`            | Partial update                   | staff + change |
| DELETE | `/api/v1/{app_label}/{model_name}/{pk}/`            | Delete                           | staff + delete |

There is **no** `PUT` in v1. Use `PATCH` for partial updates.

The `app_label`/`model_name` segments must match a model that is
registered in the configured admin site **and** that the requesting user
can view via `ModelAdmin.has_view_permission(request)` (the broader
permission gate for the path; specific operations check their own
`has_*_permission`).

---

## 2. `GET /api/v1/registry/`

Response 200:

```json
{
  "mount": "/admin-react/",
  "user": {
    "id": 42,
    "username": "alice",
    "is_staff": true,
    "is_superuser": false,
    "display_name": "Alice Example"
  },
  "apps": [
    {
      "app_label": "fintech",
      "verbose_name": "Fintech",
      "models": [
        {
          "app_label": "fintech",
          "model_name": "account",
          "verbose_name": "account",
          "verbose_name_plural": "accounts",
          "object_name": "Account",
          "permissions": {
            "view": true,
            "add": true,
            "change": true,
            "delete": false
          }
        }
      ]
    }
  ]
}
```

Rules:

- Only models registered in the configured admin site are included.
- A model is included for a user only if
  `ModelAdmin.has_module_permission(request)` and
  `ModelAdmin.has_view_permission(request)` both return truthy.
- `mount` is the absolute URL path at which the package is mounted, so the
  SPA can construct links without hardcoding.

---

## 3. `GET /api/v1/{app_label}/{model_name}/`

Query parameters:

| Name        | Type    | Default | Notes                                                            |
| ----------- | ------- | ------- | ---------------------------------------------------------------- |
| `q`         | string  | `""`    | Forwarded to `ModelAdmin.get_search_results(request, qs, q)`.    |
| `page`      | int     | `1`     | 1-indexed.                                                       |
| `page_size` | int     | `DEFAULT_PAGE_SIZE` | Clamped to `MAX_PAGE_SIZE`.                          |
| `ordering`  | string  | `""`    | Comma-separated list. Each entry must appear in `get_ordering(request)` or `ModelAdmin.ordering`. Unknown values are ignored. |
| `year`      | int     | (none)  | Date-hierarchy drill-down. Active only when the `ModelAdmin` declares `date_hierarchy`. Garbage / out-of-range silently ignored. See [§3.1](#31-date_hierarchy-optional-block). |
| `month`     | int     | (none)  | Requires `year` to be set; ignored otherwise.                    |
| `day`       | int     | (none)  | Requires `year` and `month` to be set; ignored otherwise.        |
| `<filter>`  | string  | (none)  | Admin-parity filter params (`?status__exact=…`, `?owner__id__exact=…`, `?<parameter_name>=…` for `SimpleListFilter`). See [§11](#11-list_filter-listsidebar-filters). Unknown keys silently ignored. |

Response 200:

```json
{
  "app_label": "fintech",
  "model_name": "account",
  "permissions": { "view": true, "add": true, "change": true, "delete": false },
  "columns": [
    { "name": "name",     "label": "Name",     "sortable": true  },
    { "name": "balance",  "label": "Balance",  "sortable": true  },
    { "name": "is_active","label": "Active",   "sortable": false }
  ],
  "search_fields": ["name", "iban"],
  "filters": [
    { "type": "boolean",    "name": "is_active",  "label": "Active" },
    { "type": "foreignkey", "name": "owner",      "label": "Owner",
      "to": { "app_label": "auth", "model_name": "user" } }
  ],
  "page": 1,
  "page_size": 25,
  "total": 137,
  "results": [
    {
      "pk": 1,
      "label": "Checking — Alice",
      "fields": {
        "name": "Checking — Alice",
        "balance": "1023.45",
        "is_active": true
      }
    }
  ]
}
```

Rules:

- `columns` is built from `ModelAdmin.get_list_display(request)`. Callable
  list-display values are resolved using the admin's standard helpers.
- `search_fields` is the literal list from the `ModelAdmin` (so the SPA
  can label the search box). Empty list means no search.
- `results[*].fields` only contains values for `columns[*].name`.
- `results[*].label` is `str(obj)` (the admin's display fallback).
- `total` reflects the filtered queryset count **after** search, the
  date-hierarchy drill-down (§3.1), and `list_filter` (§11) are all
  applied.
- `filters` is built from `ModelAdmin.get_list_filter(request)`. See
  [§11](#11-list_filter-listsidebar-filters) for the closed
  five-type vocabulary, URL grammar, and rules.

### 3.1 `date_hierarchy` (optional block)

When the `ModelAdmin` declares
`date_hierarchy = "<DateField-or-DateTimeField-name>"`, the response
gains a `date_hierarchy` block:

```json
"date_hierarchy": {
  "field": "created_at",
  "granularity_options": ["year", "month", "day"],
  "active": { "year": 2025, "month": 10, "day": null },
  "buckets": [
    { "value": 5,  "count": 12 },
    { "value": 20, "count":  4 }
  ]
}
```

- **`field`** — the name of the date field on the model.
- **`granularity_options`** — always `["year", "month", "day"]` (the
  closed v1 vocabulary).
- **`active`** — the currently selected drill-down levels. Children
  of a `null` ancestor are forced to `null` (e.g., `?month=10`
  without a year is ignored).
- **`buckets`** — next-level drill-down counts:
  - No year selected → buckets are years.
  - Year selected, no month → buckets are months *within that year*.
  - Year + month selected, no day → buckets are days *within that
    month*.
  - Year + month + day selected → buckets are `[]` (no further
    drill).

The block is **omitted** when:

- The admin does not declare `date_hierarchy`, **or**
- The named field does not exist on the model (defensive against
  typos), **or**
- The named field is not a `DateField` / `DateTimeField`.

Robustness: garbage query strings (`?year=abc`, `?year=-1`,
`?month=99`) are silently dropped; the endpoint never raises on a
bad query parameter. Out-of-range values are bounds-checked
(`year ∈ [1, 9999]`, `month ∈ [1, 12]`, `day ∈ [1, 31]`) before
reaching the ORM.

Note: §3.1 (`date_hierarchy`) uses bare `?year=` / `?month=` / `?day=`
params; §11 (`list_filter`) uses admin-parity `?<field>__year=` style.
They coexist on the same response without conflict — different URL
namespaces.

---

## 4. `GET /api/v1/{app_label}/{model_name}/{pk}/`

Response 200:

```json
{
  "app_label": "fintech",
  "model_name": "account",
  "pk": 1,
  "label": "Checking — Alice",
  "permissions": { "view": true, "add": true, "change": true, "delete": false },
  "fieldsets": [
    {
      "title": null,
      "fields": ["name", "balance", "is_active", "owner"]
    }
  ],
  "fields": {
    "name": {
      "type": "string",
      "label": "Name",
      "required": true,
      "readonly": false,
      "help_text": "",
      "max_length": 120,
      "value": "Checking — Alice"
    },
    "balance": {
      "type": "decimal",
      "label": "Balance",
      "required": true,
      "readonly": false,
      "help_text": "",
      "decimal_places": 2,
      "value": "1023.45"
    },
    "is_active": {
      "type": "boolean",
      "label": "Active",
      "required": false,
      "readonly": false,
      "value": true
    },
    "owner": {
      "type": "foreignkey",
      "label": "Owner",
      "required": true,
      "readonly": false,
      "to": { "app_label": "auth", "model_name": "user" },
      "value": { "id": 7, "label": "alice" }
    }
  }
}
```

Rules:

- Field set is derived from `ModelAdmin.get_form(request, obj)`'s declared
  fields, intersected with `ModelAdmin.get_fields(request, obj)` (or
  `get_fieldsets`). Anything in `exclude`/`get_exclude` is omitted.
- `readonly: true` corresponds to membership in
  `ModelAdmin.get_readonly_fields(request, obj)`.
- Field `type` is a closed v1 vocabulary:
  - `string`, `text`, `email`, `url`, `slug`, `ip`, `filepath`
  - `integer`, `float`, `decimal`, `duration`
  - `boolean`
  - `date`, `datetime`, `time`
  - `uuid`
  - `binary` (base64-encoded bytes)
  - `json` (pass-through dict; values recursively serialised)
  - `array` (pass-through list; elements recursively serialised — for
    `django.contrib.postgres.fields.ArrayField`)
  - `range` (postgres range types — `DateRangeField`, `IntegerRangeField`, …)
  - `choice`
  - `foreignkey`
  - `unsupported` (manytomany and unknown types in v1; client renders a
    read-only label and no edit control)
- For `choice` fields the response includes `"choices": [{ "value":...,
  "label":... }, ...]`.
- Sensitive-shaped field names (password, secret, token, api_key, hash,
  ...) are never serialized; the field is omitted as if `exclude`d.
  Defense-in-depth atop the form's own exclusion rules.

### 4.1 Extending the type vocabulary

Consumers can register a custom field type so the SPA serializes it
without forking the package:

```python
# yourapp/apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    def ready(self):
        from django_admin_react.api.serializers import register_field_type
        from .fields import MoneyField

        register_field_type(
            "MoneyField",       # what field.get_internal_type() returns
            "decimal",          # reuse a builtin SPA widget…
            serializer=lambda v: None if v is None else str(v.amount),
        )
```

Rules:

- The closed builtin vocabulary cannot be overridden — calling
  `register_field_type("CharField", ...)` is a silent no-op so a
  third-party app can't change `CharField` rendering for every
  consumer.
- The `serializer` argument is optional; without it, the default
  Python-type dispatch in `serialize_value` runs.
- Coin a new `vocab_type` label (e.g. `"money"`) only if you also
  ship a matching SPA widget via the frontend extension surface.

---

## 5. Write endpoints

### 5.1 `POST /api/v1/{app_label}/{model_name}/`

Request body:

```json
{ "name": "Checking — Bob", "balance": "0.00", "is_active": true, "owner": 9 }
```

- The payload keys must be a subset of the writable fields returned by the
  GET-detail equivalent for a new object (`obj=None`). Unknown keys
  produce `400`.
- For `foreignkey` fields, the value is the related object's primary key.
- The backend constructs `ModelAdmin.get_form(request)(data=payload)`,
  calls `form.is_valid()`, and on success calls
  `ModelAdmin.save_model(request, instance, form, change=False)`.
- Validation errors are returned as in §6.

Response 201:

```json
{
  "pk": 17,
  "label": "Checking — Bob",
  "redirect": "/admin-react/fintech/account/17/"
}
```

### 5.2 `PATCH /api/v1/{app_label}/{model_name}/{pk}/`

- Loads the existing object via `ModelAdmin.get_queryset(request)`.
- Builds form initial data from the existing instance.
- Merges the request body on top of that initial data.
- Validates with `ModelAdmin.get_form(request, obj)(data=merged)`.
- Saves via `ModelAdmin.save_model(request, instance, form, change=True)`.
- Readonly and excluded fields in the payload produce a `400`.

Response 200: same shape as `GET .../{pk}/`.

### 5.3 `DELETE /api/v1/{app_label}/{model_name}/{pk}/`

- Checks `has_delete_permission(request, obj)`.
- Calls `ModelAdmin.delete_model(request, obj)`.

Response 204 (no body).

---

## 6. Error format

All errors use a uniform shape:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "One or more fields are invalid.",
    "fields": {
      "balance": ["Ensure this value is greater than or equal to 0."]
    }
  }
}
```

v1 error codes:

| HTTP | `code`                  | When                                              |
| ---- | ----------------------- | ------------------------------------------------- |
| 400  | `bad_request`           | Malformed JSON, unknown keys, write-to-readonly.  |
| 400  | `validation_failed`     | Form `is_valid()` returned False.                 |
| 401  | `not_authenticated`     | (Reserved; the package usually redirects to login.) |
| 403  | `forbidden`             | CSRF or `has_*_permission` failure.               |
| 404  | `not_found`             | Model not in registry, or object not in queryset. |
| 405  | `method_not_allowed`    | e.g., PUT or HEAD.                                |
| 409  | `conflict`              | Reserved for optimistic concurrency in v1.x.      |
| 500  | `internal_error`        | Anything else. Body never includes a stack trace. |

Permission-related `403`s do **not** leak whether the object exists.

---

## 7. Pagination, ordering, search

- Pagination is offset-based and `1-indexed`. The response always
  includes `page`, `page_size`, `total`.
- Ordering is opt-in via `?ordering=...`. The backend validates each token
  against the admin's allowed ordering before applying it. Invalid tokens
  are silently dropped (not an error) so the UI keeps working.
- Search is **only** active if `ModelAdmin.search_fields` is non-empty.
  The backend calls `get_search_results(request, qs, q)` and respects
  whatever it returns (including `may_have_duplicates`, applied with
  `.distinct()` if needed).

---

## 8. Forwards compatibility

- New optional fields may be added to any response.
- Clients must ignore unknown fields rather than fail.
- No field changes name, type, or meaning without a new `api/v2/`
  namespace.

---

## 9. Examples

Curl examples (assuming session + CSRF in cookies):

```bash
curl -H "Cookie: sessionid=...; csrftoken=XYZ" \
     -H "X-CSRFToken: XYZ" \
     https://example.com/admin-react/api/v1/registry/

curl -H "Cookie: ..." -H "X-CSRFToken: ..." \
     -X PATCH \
     -H "Content-Type: application/json" \
     -d '{"name":"Renamed"}' \
     https://example.com/admin-react/api/v1/fintech/account/17/
```

---

## 11. `list_filter` (list-sidebar filters)

Closes consumer feedback issue
[#56](https://github.com/MartinCastroAlvarez/django-admin-react/issues/56).

The list endpoint surfaces `ModelAdmin.get_list_filter(request)` as the
`filters: []` array (§3) so the SPA can render the legacy admin's
left-sidebar filter bar. Filter application reuses Django's own
`ChangeList` spec construction — never a parallel filter system, never
hand-rolled `Q`-AND iteration (which would silently break every
`SimpleListFilter` subclass a consumer ships).

### 11.1 The five-type closed vocabulary

Every descriptor in `filters[]` is one of five `type` values. The SPA
only ever learns five layouts; anything Django returns outside this
set is silently dropped.

| `type`        | When                                                                                            | Extra fields |
| ------------- | ----------------------------------------------------------------------------------------------- | ------------ |
| `boolean`     | `BooleanField` filter.                                                                          | — |
| `choices`     | Field with `choices=` declared on the model.                                                    | `choices: [{value, label}]` |
| `foreignkey`  | `ForeignKey` / `OneToOneField` filter (or `RelatedFieldListFilter`).                            | `to: {app_label, model_name}` |
| `date_range`  | `DateField` / `DateTimeField` filter.                                                           | — |
| `custom`      | `SimpleListFilter` subclass.                                                                    | `lookups: [{value, label}]` |

Every descriptor also carries `name` (a stable identifier the SPA uses)
and `label` (the human-readable title from the admin or the model
field's `verbose_name`).

### 11.2 URL grammar — admin-parity

Filter selections are passed as query params with the **same shape
Django admin uses**. A URL copied from the legacy admin lands on the
same row set in the SPA — operators can keep saved admin links
working.

| `type`        | Example query string                              |
| ------------- | ------------------------------------------------- |
| `boolean`     | `?is_active__exact=1` (1 = True, 0 = False)       |
| `choices`     | `?status__exact=open`                             |
| `foreignkey`  | `?owner__id__exact=42`                            |
| `date_range`  | `?created_at__year=2026`, `?created_at__gte=2026-01-01`, `?created_at__lte=2026-12-31` |
| `custom`      | `?<parameter_name>=<value>` (whatever the `SimpleListFilter` subclass declares) |

Multiple filters in the same URL combine with **AND** — matching the
admin's convention. Mutually exclusive options within one filter (e.g.
choosing two values for the same `choices` filter) is **not** supported
in v1.

### 11.3 Robustness rules

- **Unknown query params are silently ignored.** A hostile `?bogus=42`
  is a no-op, never a 400. Django's filter machinery only consults the
  params each spec declares in `expected_parameters()`.
- **A misconfigured `list_filter` entry never 500s the endpoint.** A
  non-existent field name, an exception in `SimpleListFilter.lookups()`,
  or any other construction error is swallowed and the entry dropped
  from the descriptor list. The valid entries on the same admin still
  surface. (Rule 12 / S-11.)
- **`SimpleListFilter.queryset(request, qs)` is honored.** This is the
  architectural correctness rule that motivated using `ChangeList` spec
  construction: a custom filter that joins through a related table,
  applies a complex `Q`, or annotates the queryset will run exactly the
  code the consumer wrote.

### 11.4 Permission posture

Filter application happens **after** `ModelAdmin.get_queryset(request)`
has already narrowed the queryset to the rows this user may see (rule
10). Filters can only narrow further — they never broaden, never
escape `has_view_permission`. An attacker who crafts `?owner__id__exact=<other-user>`
on a model they are not authorized to view does not get a permission
oracle: the query simply returns the intersection of the allowed
queryset and the filter, which may be empty.

### 11.5 Out of scope for v1

- Hierarchical filters / drill-down lists (see issue
  [#62](https://github.com/MartinCastroAlvarez/django-admin-react/issues/62)
  for `date_hierarchy`).
- Saved filter sets per user.
- Multi-value selection within a single filter (`?status__exact=open&status__exact=closed`
  — accepted by Django via `?status__in=open,closed` in some setups,
  but kept out of v1 to keep the SPA's rendering surface tight).

