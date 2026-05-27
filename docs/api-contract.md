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

The registry endpoint walks `admin_site.get_app_list(request)` to build
the navigation tree. Django's default implementation groups by the real
`app_label`; a consumer that subclasses `AdminSite` and overrides
`get_app_list` to regroup or curate models (a very common pattern in
production admins) has that grouping honoured by the SPA. This means
the SPA navigation matches the HTML admin's navigation 1:1.

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
      "name": "Fintech",
      "app_label": "fintech",
      "verbose_name": "Fintech",
      "is_group": false,
      "models": [
        {
          "app_label": "fintech",
          "real_app_label": "fintech",
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

When the consumer's `AdminSite.get_app_list` returns synthetic groups
(e.g. `"Loans"` containing `packages.LoanPackage` + `documents.Document` +
`statements.BankStatement`), the `apps[]` entry surfaces the group name
and a synthetic `app_label`, while each model entry keeps the **real**
`(real_app_label, model_name)` the SPA needs to construct API URLs:

```json
{
  "apps": [
    {
      "name": "Loans",
      "app_label": "loans",
      "verbose_name": "Loans",
      "is_group": true,
      "models": [
        {
          "app_label": "loans",
          "real_app_label": "packages",
          "model_name": "loanpackage",
          "object_name": "LoanPackage",
          "verbose_name": "loan package",
          "verbose_name_plural": "loan packages",
          "permissions": { "view": true, "add": true, "change": true, "delete": false }
        }
      ]
    }
  ]
}
```

Rules:

- The registry walks `admin_site.get_app_list(request)`. Consumer overrides
  of that method are honoured as-is — both the grouping shape and the
  per-model filtering Django already performs inside `get_app_list`
  (`has_module_permission` + `has_view_permission`).
- Only models registered in the configured admin site appear (Django's
  `get_app_list` already enforces this — `_registry` is the only model
  source).
- `app_label` on an `apps[]` entry is the group's identifier — Django's
  real app label when grouping is the default, or the consumer's synthetic
  label when `get_app_list` was overridden.
- `name` is the human-readable group name from `get_app_list` (Django's
  default returns `apps.get_app_config(app_label).verbose_name`).
- `is_group` is `true` when the entry's `app_label` does **not** appear in
  `apps.get_app_configs()` — i.e., the consumer coined it inside their
  `get_app_list` override. `false` otherwise. The SPA may use this hint to
  style synthetic groups differently if it wants; functionally `is_group`
  is informational.
- Each model entry carries `real_app_label`, which is **always** the
  `model._meta.app_label` of the underlying Django model. The SPA builds
  list / detail URLs as `<mount>/api/v1/<real_app_label>/<model_name>/`.
  In the default (no `get_app_list` override) case, `real_app_label ==`
  the surrounding `app_label`; in synthetic-group cases they differ.
- `mount` is the absolute URL path at which the package is mounted, so the
  SPA can construct links without hardcoding.

Backwards compatibility: when the consumer has not overridden
`get_app_list`, the only shape changes from earlier `0.1.0a*` versions are
the new fields (`name`, `is_group`, `real_app_label`). All existing
clients that key off `app_label` + `model_name` continue to work; the
new fields are additive.

Reserved-label note: synthetic groups whose `app_label` collides with
`RESERVED_APP_LABELS` (`registry`, `schema`, `session`) are surfaced
unchanged in the registry response but their per-model `real_app_label`
must still resolve via the real Django app label. A consumer naming a
synthetic group `session` does **not** collide with the optional session
endpoints because the package's URL resolver matches `session/` to its
own view before any `<app_label>/<model_name>/` pattern.

---

## 3. `GET /api/v1/{app_label}/{model_name}/`

Query parameters:

| Name        | Type    | Default | Notes                                                            |
| ----------- | ------- | ------- | ---------------------------------------------------------------- |
| `q`         | string  | `""`    | Forwarded to `ModelAdmin.get_search_results(request, qs, q)`.    |
| `page`      | int     | `1`     | 1-indexed.                                                       |
| `page_size` | int     | `DEFAULT_PAGE_SIZE` | Clamped to `MAX_PAGE_SIZE`.                          |
| `ordering`  | string  | `""`    | Comma-separated list. Each entry must appear in `get_ordering(request)` or `ModelAdmin.ordering`. Unknown values are ignored. |
| `year`      | int     | (none)  | Date-hierarchy drill-down. Active only when the `ModelAdmin` declares `date_hierarchy`. Garbage / out-of-range silently ignored. |
| `month`     | int     | (none)  | Requires `year` to be set; ignored otherwise.                    |
| `day`       | int     | (none)  | Requires `year` and `month` to be set; ignored otherwise.        |

Response 200:

```json
{
  "app_label": "fintech",
  "model_name": "account",
  "pk_field": "id",
  "permissions": { "view": true, "add": true, "change": true, "delete": false },
  "columns": [
    { "name": "name",     "label": "Name",     "sortable": true  },
    { "name": "balance",  "label": "Balance",  "sortable": true  },
    { "name": "is_active","label": "Active",   "sortable": false }
  ],
  "search_fields": ["name", "iban"],
  "search_help_text": "Search by name or IBAN.",
  "page": 1,
  "page_size": 25,
  "total": 137,
  "full_count": 412,
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

- `pk_field` names the model's primary-key field (`model._meta.pk.name`,
  usually `id`). When it appears in `columns`, the SPA pins that column
  first, never truncates it, and keeps it from being hidden.
- `columns` is built from `ModelAdmin.get_list_display(request)`. Callable
  list-display values are resolved using the admin's standard helpers.
- `list_display_links` (`#251`) is the column name(s) that link to the
  detail page — `ModelAdmin.get_list_display_links` (defaults to the first
  column; `[]` when the admin set `list_display_links = None` to disable
  linking). The SPA links exactly these columns. Callable list_display
  entries are dropped (only string column names round-trip).
- `search_fields` is the literal list from the `ModelAdmin` (so the SPA
  can label the search box). Empty list means no search.
- `search_help_text` is `ModelAdmin.search_help_text` (empty string when
  unset) — the SPA renders it under the search box, matching Django's
  changelist (`#445`).
- `total` is the count *after* search / `list_filter` / `date_hierarchy`
  narrowing. `full_count` is the unfiltered base count
  (`ModelAdmin.get_queryset(request)`), so the SPA can show "<total> of
  <full_count>" when the list is narrowed (`show_full_result_count`
  parity). It equals `total` when the list isn't narrowed, and is `null`
  when the `ModelAdmin` sets `show_full_result_count = False` (the opt-out
  for tables where the extra `COUNT(*)` is too expensive).
- `results[*].fields` only contains values for `columns[*].name`.
- `results[*].label` is `str(obj)` (the admin's display fallback).
- **ForeignKey cells (`#184`):** a FK cell value is
  `{ "id": <pk>, "label": "<str(related)>" }`. The envelope also carries
  `"to": { "app_label": "<real>", "model_name": "..." }` — so the SPA
  renders the cell as a link to `<mount>/<app_label>/<model_name>/<id>`
  — **only when** the related model is registered on the configured
  admin site **and** the requesting user has `has_view_permission` on
  that target model (`#301`). `to` is **omitted** otherwise: the SPA
  shows plain text rather than a link the detail endpoint would `403`/`404`
  on, and the response never leaks the adjacency / identity of a model
  the user can't reach (extends the `#89` filter-descriptor guard to a
  per-user check). The `label` is always present — the related *object*
  is visible in the cell by design, matching Django's changelist.
  `app_label` is the real `_meta.app_label` the detail URL resolves
  against.
- `total` reflects the filtered queryset count **after** search **and
  date-hierarchy drill-down** are applied.

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

### 3.4 `actions` (always-present array)

When the `ModelAdmin` declares `actions = [...]`, the list response
surfaces each action so the SPA can render the "Actions" dropdown
above the list table. The key is always present (empty `[]` when the
admin has no actions visible to the user).

```json
"actions": [
  { "name": "delete_selected", "label": "Delete selected users",
    "description": "Delete selected users", "requires_confirmation": true },
  { "name": "mark_inactive",   "label": "Mark inactive",
    "description": "Mark inactive", "requires_confirmation": false }
]
```

- `name` — the action's identifier (the function's `__name__`, or
  the explicit name from `@admin.action(name=...)`). This is the
  segment in the runner URL.
- `label` — the user-facing string (from `short_description` or
  fall back to the name).
- `requires_confirmation` — `True` when the label contains "delete"
  (conservative hint; the SPA may always show a confirmation step
  regardless).

The set is the result of `ModelAdmin.get_actions(request)` — Django
filters out actions whose required permission the user lacks, so the
SPA never sees an action it can't run.

### 3.3 `filters` (always-present array)

When the `ModelAdmin` declares `list_filter`, the response surfaces
per-filter metadata so the SPA can render the left-sidebar filter
strip. The key is always present (empty `[]` when no filters
declared) so the SPA branches on `filters.length` without a
`hasOwnProperty` guard.

```json
"filters": [
  { "name": "is_staff",      "label": "Staff status",  "type": "boolean" },
  { "name": "status",        "label": "Status",        "type": "choice",
    "choices": [{"value": "active", "label": "Active"}, ...] },
  { "name": "owner",         "label": "Owner",         "type": "foreignkey",
    "to": {"app_label": "auth", "model_name": "user"},
    "choices": [{"value": 1, "label": "alice"}] },
  { "name": "created_at",    "label": "Created",       "type": "date" },
  { "name": "active_state",  "label": "Active state",  "type": "custom",
    "selected": "exclude",
    "lookups": [{"value": "yes", "label": "Active"}, {"value": "no", "label": "Inactive"}] }
]
```

Supported v1 filter types:

- **`boolean`** — three-way; param value is `true` / `false` (anything
  else, including unset, leaves the queryset alone).
- **`choice`** — exact match against the field's `choices`.
- **`foreignkey`** — exact pk match. Inlines up to 25 options when
  the target table is small; larger targets defer to autocomplete
  (#59) — `choices` is absent then, and the descriptor instead carries
  **`autocomplete: true`** (`#282`) when the target admin declares
  `search_fields` (so the SPA drives the filter through the
  `…/autocomplete/` endpoint §3.2). When the large target has no
  `search_fields`, neither `choices` nor `autocomplete` is present
  (the endpoint would `400`).
- **`date`** — exact-date match. Range UX deferred (use
  `date_hierarchy` for the heavy date-drill case — §3.1).
- **`custom`** — `SimpleListFilter` subclass. The filter's own
  `parameter_name` is the query string key; `lookups()` is the
  choice list; `queryset()` does the narrowing. `selected` carries the
  filter's currently-applied lookup (`filter.value()`), **including a
  default it applies when no querystring param is present** — so the SPA
  reflects that default as selected rather than showing "All" while the
  backend silently narrows the rows. `null` when nothing is selected.
  (Field-based filters have no server-side default; their selection is
  the URL param, so they omit `selected`.)

Each filter's value comes from `?<param_name>=<value>`. Unknown
filter params are silently ignored. Garbage values that break the
ORM fall back to `.none()` (zero rows; never a 500). Filters are
applied **after** search and **before** `date_hierarchy` /
ordering.

A `list_filter` entry may be a **related-field path** that spans
relations (`"author__is_active"`, `"order__customer__country"`), not just
a direct field (`#440`). The descriptor's `name` is the full path and the
SPA round-trips `?<path>=<value>`; the leaf field's type picks the filter
shape (boolean / choice / foreignkey / date), and a sensitive leaf
(`author__password`) is dropped like any sensitive field. Transform
lookups (`__year`, `__gte`, `__icontains`) are not yet supported and are
silently skipped.

### 3.2 `GET /api/v1/{app_label}/{model_name}/autocomplete/`

Typeahead endpoint for high-cardinality FK pickers
(`autocomplete_fields` / `raw_id_fields`). Powered by the **target**
admin's `search_fields` + `get_search_results`; the package never
re-implements search semantics.

Query parameters:

| Name        | Type    | Default | Notes                                                            |
| ----------- | ------- | ------- | ---------------------------------------------------------------- |
| `q`         | string  | `""`    | Forwarded to target `ModelAdmin.get_search_results(request, qs, q)`. |
| `page`      | int     | `1`     | 1-indexed.                                                       |
| `page_size` | int     | `20`    | Clamped to `min(50, MAX_PAGE_SIZE)` — typeahead-specific cap.    |

Response 200:

```json
{
  "results": [
    { "id": 7,  "label": "alice" },
    { "id": 12, "label": "alfred" }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "has_more": false
  }
}
```

- `has_more` is computed via a fetch-one-extra trick (no `COUNT(*)`
  on every keystroke).
- `label` is `str(obj)` (admin's display fallback).
- Returns `400 bad_request` when the target admin doesn't declare
  `search_fields` — same condition Django's stock
  `AdminSite.autocomplete_view` raises as `ImproperlyConfigured`.

Permission posture: gated by the **target** model's
`has_view_permission` — the user can autocomplete into `auth.User`
only if their view permission on `User` allows it. Unviewable target
is 404 (not 403) so the endpoint doesn't reveal "this model exists
but you can't see it" (Rule 12).

`Cache-Control: no-store` (per-user, search-term-specific payload).

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
  "save_options": {
    "show_save": true,
    "show_save_and_continue": true,
    "show_save_and_add_another": true,
    "show_save_as_new": false,
    "save_as": false,
    "save_as_continue": true
  },
  "password_change": { "supported": false },
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

- `save_options` mirrors Django admin's save-flow buttons (`#154`). It
  is computed from `ModelAdmin` permission methods + `ModelAdmin.save_as`,
  matching `django.contrib.admin`'s `submit_row` logic for the change
  view (`add=False, change=True`):
  - `show_save` — `has_change_permission(request, obj)` on the change
    view.
  - `show_save_and_continue` — `show_save and has_view_permission`.
  - `show_save_and_add_another` — `has_add_permission and not save_as`
    (Django suppresses "add another" on the change view when `save_as`).
  - `show_save_as_new` — `has_change_permission and save_as`.
  - `save_as` / `save_as_continue` — the raw `ModelAdmin` flags, so the
    SPA knows whether a "Save as new" POST creates a fresh object and
    where it lands afterward.
  The SPA renders exactly the buttons that are `true`; the backend
  re-checks the relevant `has_*_permission` on the actual POST/PATCH —
  `save_options` is a UI hint, not the gate. Inline-formset editability
  is not yet factored in (the inline write-half is tracked under `#54`);
  for models without editable inlines the flags are exact.
- `prepopulated_fields` (`#245`, **add form only** — `GET .../add/`) is
  `{target: [sources]}` from `ModelAdmin.prepopulated_fields`, restricted
  to rendered, non-readonly targets and rendered sources. The SPA
  slugifies the target field from its sources' values while the user
  types, stopping once the target is edited by hand. Always present
  (empty `{}` when the admin declares none); a pure UI affordance — the
  backend does not auto-fill on write.
- `password_change.supported` (`#252`) is `true` only when the model's
  admin declares a `change_password_form` (i.e. a `UserAdmin`) **and**
  the request holds change permission on the object — the SPA shows
  "Set password" exactly when `POST .../{pk}/password/` (§5.6) would be
  accepted. It is a capability flag only; no password material is ever
  surfaced (the field itself stays hidden by the sensitive-name
  denylist). For every non-user model it is `false`.
- Field set is derived from `ModelAdmin.get_form(request, obj)`'s declared
  fields, intersected with `ModelAdmin.get_fields(request, obj)` (or
  `get_fieldsets`). Anything in `exclude`/`get_exclude` is omitted.
- `readonly: true` corresponds to membership in
  `ModelAdmin.get_readonly_fields(request, obj)`.
- `widget` is an optional **presentational** hint (`#251`): `"radio"` when
  the admin lists the field in `ModelAdmin.radio_fields` (render the
  choice/FK as radio buttons), or `"raw_id"` when it's in
  `ModelAdmin.raw_id_fields` (render a pk input + lookup for a
  high-cardinality FK/M2M, instead of a select). `radio_fields` wins if a
  field is in both. Absent when the field is in neither; it changes no
  value, type, or permission gate.
- `empty_value_display` (top-level, also on the **list** response §3) is the
  admin's placeholder for empty/null values — `ModelAdmin.empty_value_display`
  if set, else the `AdminSite` default (`"-"`) (`#251`). The SPA renders this
  instead of a hardcoded em-dash. Always present.
- Field `type` is a closed v1 vocabulary:
  - `string`, `text`, `email`, `url`, `slug`, `ip`, `filepath`
  - `integer`, `float`, `decimal`, `duration`
  - `boolean`
  - `date`, `datetime`, `time`
  - `uuid`
  - `binary` (base64-encoded bytes). **Read-only in v1.** The SPA renders
    the value as a hex preview + byte count; writes to a `BinaryField`
    from the SPA return `400 bad_request`.
  - `json` (raw object on the wire — the SPA does `JSON.stringify` for
    display and `JSON.parse` for writes; the server re-validates via
    Django's `JSONField.to_python` so the wire format is canonical
    JSON, not Python repr).
  - `array` (pass-through list; elements recursively serialised — for
    `django.contrib.postgres.fields.ArrayField`).
  - `range` (postgres range types — `DateRangeField`, `IntegerRangeField`,
    `DateTimeRangeField`, `DecimalRangeField`). Wire shape:
    `{"subtype": "daterange"|"intrange"|"datetimerange"|"numrange",
    "value": {"lower": ..., "upper": ..., "bounds": "[)"}}`. The
    `bounds` string uses Postgres's four-char closed vocabulary —
    one of `"[]"`, `"[)"`, `"(]"`, `"()"`. `lower` and `upper` are
    serialised in the inner subtype's format (e.g., `date` for
    `daterange`, ISO 8601 for `datetimerange`).
  - `choice`
  - `foreignkey`
  - `manytomany` — list of `{id, label}` envelopes. Writable with a
    list of bare pks (or `[{id, label}, ...]` echo-back). Pure M2M
    only — M2M with a custom `through` model that has extra columns
    falls back to `unsupported` (manage via the through admin).
  - `file` / `image` — `{name, url, size}` envelope (or `null` when
    empty). `url` defers to the consumer's storage backend
    (`value.url`) so signed-URL backends (S3, GCS, …) work without
    package changes. `size` is best-effort (`null` when the backend
    can't expose it cheaply). **v1 surfaces the read side**;
    multipart upload + clearing is on the roadmap.
  - `unsupported` (unknown types in v1; client renders a read-only
    label and no edit control)
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
- **Reusing an existing `vocab_type`** (the example above maps
  `MoneyField` → `"decimal"`) works out of the box — the SPA already
  has a `decimal` widget.
- **Coining a brand-new `vocab_type`** (e.g. `"money"`) requires the
  consumer to also ship a matching SPA renderer via the frontend
  extension surface — see issue
  [#65](https://github.com/MartinCastroAlvarez/django-admin-react/issues/65).
  Without a matching widget the SPA falls back to rendering the value
  as a read-only `unsupported` tile, mirroring the v1 fallback for
  manytomany.

---

### 4.2 `inlines` (always-present array)

When the `ModelAdmin` declares `inlines = [...]`, the detail response
surfaces each `InlineModelAdmin` so the SPA can render the parent +
children together. The key is always present (empty `[]` when no
inlines declared).

```json
"inlines": [
  {
    "name": "comment_set",
    "label": "comments",
    "kind": "tabular",
    "fk_name": "post",
    "child": { "app_label": "blog", "model_name": "comment" },
    "extra": 1,
    "min_num": 0,
    "max_num": null,
    "can_view": true,
    "can_add": true,
    "can_change": true,
    "can_delete": true,
    "fields": [
      { "name": "text",       "label": "Text",       "readonly": false },
      { "name": "created_at", "label": "Created at", "readonly": true  }
    ],
    "rows": [
      { "pk": 7, "label": "Comment object (7)",
        "fields": { "text": "Hi!", "created_at": "2025-10-01T12:00:00+00:00" } }
    ]
  }
]
```

- **`kind`** is `tabular` or `stacked`.
- **`fk_name`** is the FK on the child that points back at the
  parent (declared via `InlineModelAdmin.fk_name` or auto-detected
  by scanning the child's FKs).
- **`can_view` / `can_add` / `can_change` / `can_delete`** come from
  the child's `has_*_permission(request, obj=parent)` — when the
  child's `has_view_permission` is false, `rows` is `[]` (no
  surface to a model the user can't see, per Rule 5).
- **`fields`** is the inline's visible-fields set (`get_fields` minus
  `get_exclude` minus the implicit parent FK minus the sensitive-name
  denylist). Each entry is `{name, label, readonly, type, required}` —
  `type` reuses the §4 field-type vocabulary and `required` mirrors the
  form layer (`not field.blank`), so the SPA renders a typed input per
  inline field in edit mode (same `FieldInput` widget as top-level
  fields). `type` / `required` are additive — pre-enrichment clients
  that only read `name`/`label` keep working.
- **`rows`** are the existing children gated by the inline's own
  `get_queryset` (Rule 10).

**Write support** is the inline write path documented in §5.2.1 — a
`PATCH` body's `inlines` object round-trips children through the
formset. The read shape above + the `type`/`required` field metadata
are what the SPA needs to render the editable inline forms.

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
  `ModelAdmin.save_model(request, instance, form, change=False)` then
  `ModelAdmin.save_related(...)`.
- Validation errors are returned as in §6.
- **File uploads (`FileField` / `ImageField`, #241):** send the create as
  **`multipart/form-data`** instead of JSON. Scalars go in the form body,
  files in the file parts; the backend feeds `request.POST` + `request.FILES`
  to the same `ModelForm`, so the file is stored through the field's
  configured `Storage` (which sanitises the filename — no path traversal).
  A file part addressed to a readonly / excluded / unknown field is rejected
  `400`, exactly like a scalar key. CSRF still applies (the `X-CSRFToken`
  header travels with the multipart request).
- **Inline children (#403):** a JSON create body may carry an optional
  `inlines` object — the same shape as the update path (§5.2.1) — and the
  parent + its inline formsets are saved in **one transaction**. A child
  permission denial (`403`) or formset validation failure (`400`,
  `{"inlines": {...}}`) rolls back the parent create too, so a failed
  request never leaves an orphaned parent. (Inlines are JSON-only; the
  multipart file-upload path doesn't carry them.)

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

#### 5.2.1 Inline writes (Issue #54 write half)

A `PATCH` body may carry an optional top-level `inlines` object to
add / edit / delete the parent's inline children in the **same atomic
request**. It is keyed by the inline `name` the detail response emits
under §4.2 (e.g. `content_type_set`), and each block carries an
`items` list whose rows use the three Django-formset states:

```json
{
  "inlines": {
    "<inline name from §4.2>": {
      "items": [
        { "pk": null, "fields": { "<name>": <value> } },   // add
        { "pk": 7,    "fields": { "<name>": <value> } },    // change
        { "pk": 9,    "DELETE": true }                       // delete
      ]
    }
  }
}
```

Rules (enforced by `api/inlines_write.py`):

- Writes round-trip through `InlineModelAdmin.get_formset(request,
  obj=parent)` + `formset.save()` — never a per-row `save()` loop — so
  the consumer's formset `clean()` / `save_formset` hooks and signals
  run exactly as in the HTML admin's change view.
- Each row **state** is gated by the inline's own permission method
  against the parent: a new row needs `has_add_permission`, an edited
  row needs `has_change_permission`, a `DELETE` row needs
  `has_delete_permission`. A single failing gate returns `403` and
  **rolls back the entire PATCH** (the parent field changes too —
  the whole thing is one `transaction.atomic()`).
- An `inlines` key that doesn't match a declared inline returns `400`
  (deny-by-default; never silently ignored). A malformed `items`
  shape returns `400`, not `500`.
- A formset validation failure returns `400` with the per-inline
  errors under `error` and persists nothing.

Out of scope for v1 (return a follow-up issue, not silent acceptance):
nested inlines, `GenericInlineModelAdmin`, and M2M-through inlines
with extra fields. Create-with-inlines (inlines on `POST`) is a
follow-up; this half covers `PATCH` on an existing parent.

### 5.5 `PATCH /api/v1/{app_label}/{model_name}/bulk/`

Bulk update of multiple rows in one transaction. Powers
``list_editable`` and any consumer-built bulk-edit flow.

Request body:

```json
{
  "updates": [
    { "pk": 7,  "fields": { "is_active": false } },
    { "pk": 12, "fields": { "is_active": false } }
  ]
}
```

- `updates` — non-empty list, ≤ 200 entries (bulk cap).
- Each entry: `pk` required, `fields` non-empty object.
- `fields` may only name fields in `ModelAdmin.list_editable` — this
  endpoint backs the changelist's inline-editable cells, so it mirrors
  Django (a changelist POST only accepts `list_editable` names). A field
  that's writable on the *change form* but not in `list_editable` (or any
  field when `list_editable` is empty) is rejected `bad_request`, leaving
  the row unchanged (`#401`). Read-only / excluded / sensitive-name keys
  are rejected as before (§5.2).

Response 200:

```json
{
  "results": [
    { "pk": 7,  "ok": true },
    { "pk": 12, "ok": true }
  ],
  "summary": { "accepted": 2, "rejected": 0 }
}
```

On partial failure, the **entire batch rolls back** and each accepted
row's entry gains `"rolled_back": true` so the SPA knows the update
did not persist:

```json
{
  "results": [
    { "pk": 7,  "ok": false, "rolled_back": true },
    { "pk": 12, "ok": false,
      "error": { "code": "validation_failed", "message": "...",
                 "fields": { "name": ["This field is required."] } } }
  ],
  "summary": { "accepted": 0, "rejected": 2 }
}
```

Rules:

- Each row goes through `ModelAdmin.get_form()` + `save_model(change=True)`
  — same path as single-row PATCH (§5.2). Signals, audit hooks, and
  custom `save_model` overrides all fire.
- Each row is gated by `has_change_permission(request, obj)` — a row
  the user can't edit fails the batch.
- Each row's queryset starts at `ModelAdmin.get_queryset(request)`
  (Rule 10) — a row the user can't see is `not_found`.
- `readonly` / `exclude` / sensitive-named keys in any row payload
  produce that row's `bad_request` error.
- CSRF required (PATCH; no `@csrf_exempt`).
- `Cache-Control: no-store`.

### 5.4 `POST /api/v1/{app_label}/{model_name}/actions/{action_name}/`

Runs a `ModelAdmin` action over a selected set of rows. The action
name is re-resolved through `ModelAdmin.get_actions(request)` — the
SPA's name is never trusted as a callable lookup.

Request body:

```json
{ "pks": [1, 2, 3], "confirmed": true }
```

- `pks` — non-empty list of primary keys; missing or empty → `400`.
- `confirmed` — informational; the action callable owns its
  confirmation semantics. The backend doesn't short-circuit on
  `false`.

Response 200:

```json
{
  "executed": true,
  "action": "mark_inactive",
  "pks": [1, 2, 3],
  "messages": [{ "level": "success", "message": "3 users were deactivated." }]
}
```

`messages` carries any output the action queued via
`ModelAdmin.message_user` (always present, `[]` when none); the SPA toasts
each by `level` (Django's `success` / `info` / `warning` / `error` /
`debug`) so an action can talk back, matching the HTML admin (`#442`).

When the action callable returns an `HttpResponse` (e.g., a redirect
to a confirmation page in legacy admin), the JSON envelope surfaces
the redirect target:

```json
{ "executed": true, "action": "delete_selected", "redirect": "/admin-react/library/book/" }
```

Rules:

- **Rule 10 preserved**: the queryset passed to the action is
  `ModelAdmin.get_queryset(request).filter(pk__in=pks)`. The action
  cannot reach rows outside the admin's gate, even if the client
  includes their pks in the request body.
- **Rule 5**: gated by the admin's `has_change_permission`. The set
  of actions returned by `get_actions` may further narrow this per
  Django's standard behavior (e.g., `delete_selected` requires
  `has_delete_permission`).
- **CSRF**: required (`X-CSRFToken` on the POST). The endpoint is
  not `@csrf_exempt`.

Wrapped in `transaction.atomic()`.

### 5.3 `DELETE /api/v1/{app_label}/{model_name}/{pk}/`

- Checks `has_delete_permission(request, obj)`.
- Calls `ModelAdmin.delete_model(request, obj)`.

Response 204 (no body).

### 5.6 `POST /api/v1/{app_label}/{model_name}/{pk}/password/`

Set/change one object's password — `UserAdmin` parity (`#252`). A thin
JSON shell over the admin's **own** `change_password_form` (Django's
`AdminPasswordChangeForm`); the package invents no password machinery
(see §7 for the same delegation principle behind login/logout).

Request body:

```json
{ "password1": "new-secret", "password2": "new-secret" }
```

- Available **only** when the model's admin declares a
  `change_password_form` (a `UserAdmin`). For any other model this route
  returns **404** — there is no `/password/` sub-resource, mirroring
  Django's router. Check `password_change.supported` (§4) before showing
  the affordance.
- Gates: staff + `AdminSite.has_permission` (403) → model resolved via
  `_registry` (404) → object via `ModelAdmin.get_object` (404) →
  `has_change_permission(request, obj)` (403). CSRF enforced (no
  `@csrf_exempt`).
- Validation runs the admin form: `password1`/`password2` must match and
  must pass the consumer's `AUTH_PASSWORD_VALIDATORS`. Failures return
  **400** `validation_failed` with per-field errors keyed by
  `password1` / `password2` — never the value.
- `form.save()` hashes via `user.set_password`; nothing is stored in
  plaintext. When the actor changes their **own** password the session
  auth hash is rotated (`update_session_auth_hash`) so they stay logged
  in. A `LogEntry` CHANGE row ("Changed password.") is written, matching
  the legacy admin.

Response 200:

```json
{ "detail": "Password set.", "id": 7 }
```

The password is **never** read back — not in this response, not in any
read endpoint (the field stays hidden by the sensitive-name denylist).

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
| 403  | `forbidden`             | CSRF or `has_*_permission` failure on a request that was never authenticated, or an authenticated user that lacks the permission. |
| 403  | `session_expired`       | Request carried a session cookie but the user resolved to anonymous. SPA should render a re-login modal and return the user to the same path after sign-in. See §6.1 (detection) and §10 (`?next=` + optional warning toast). |
| 404  | `not_found`             | Model not in registry, or object not in queryset. |
| 405  | `method_not_allowed`    | e.g., PUT or HEAD.                                |
| 409  | `conflict`              | A write hit a DB `IntegrityError` the form didn't catch — a uniqueness/constraint race, or a DB-level constraint not mirrored in form validation (`#404`). On the bulk endpoint it appears as a per-row error. The message is generic (never echoes the driver's text). Also reserved for optimistic concurrency in v1.x. |
| 500  | `internal_error`        | Anything else. Body never includes a stack trace. |

Permission-related `403`s do **not** leak whether the object exists.

### 6.1 Session-expiry contract

The package detects a stale session by inspecting the request's
session cookie *and* the resolved user:

- **No session cookie** + anonymous user → `forbidden`. The SPA's
  normal login-redirect path applies.
- **Session cookie present** + anonymous user → `session_expired`.
  The cookie was issued by a previous, now-invalid session (manual
  logout from another device, server-side flush, session-age expiry,
  …). The SPA shows a re-login modal whose post-login redirect
  brings the user back to the same SPA URL.
- **Session cookie present** + authenticated user (any permission
  level) → `forbidden`. The user is signed in; they just lack the
  required permission. SPA shows an inline access-denied message,
  not a re-login modal.

The detection is read-only: the package never touches the session
backend to make this determination — it only inspects the cookie
name (from `settings.SESSION_COOKIE_NAME`) and `request.user`.
That keeps the check cheap and side-effect-free on every 403.

Consumers using a non-default session backend (e.g. signed-cookie
sessions, custom auth middleware) get the same envelope as long as
their middleware populates `request.user` to an anonymous user when
the session is invalid.

---

## 6.2 `GET /api/v1/schema/`

OpenAPI 3.1 document for the wire envelope shapes (registry, list,
detail, errors, filter / action / column / date-hierarchy specs,
field-type vocabulary). Drives typed-client generation (e.g.
`openapi-typescript`).

- **Does not** enumerate the consumer's models — that surface lives
  on the model-list endpoint, which is permission-gated.
- **Staff-gated** like the rest of the API.
- `Cache-Control: no-store`.

The endpoint exists so a typed client can be auto-generated rather
than hand-translated from this Markdown. CI / build pipelines can
diff the schema across versions to detect contract drift.

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

## 10. Session-expiry — SPA flow & optional warning

This section **supplements §6.1** (which defines the detection
logic and the `session_expired` envelope) with the SPA-side flow,
the `?next=` round-trip posture, and the optional pre-expiry
warning endpoints. Closes
[#63](https://github.com/MartinCastroAlvarez/django-admin-react/issues/63);
the wire-shape detection landed in
[#95](https://github.com/MartinCastroAlvarez/django-admin-react/pull/95).

### 10.1 `?next=` round-trip

When the SPA receives `error.code: "session_expired"` (HTTP 403,
per §6.1), it redirects the user to the configured Django admin
login URL with a `?next=` parameter carrying the **current SPA
route path** (not the API endpoint that returned 403). After login,
Django's login view honours `?next=` and bounces the user back to
the SPA, which hydrates from cache and resumes the prior view.

**`?next=` whitelist:** the package never echoes `?next=` from the
client back to a redirect response. The SPA constructs the
`?next=<spa-path>` itself from `window.location` (same-origin by
construction); the Django admin login view's existing
`url_has_allowed_host_and_scheme` validation is authoritative.
No open-redirect surface is added by the package. See
[`SECURITY.md`](../SECURITY.md) §4.1 for the broader posture.

### 10.2 Optional session-warning endpoints

The package may expose two optional endpoints for a pre-expiry
"Stay signed in" UX:

| Method | Path                            | Purpose                                                  | Auth         |
| ------ | ------------------------------- | -------------------------------------------------------- | ------------ |
| GET    | `/api/v1/session/`              | Returns `{ "expires_at": "<ISO8601>" }` for the current user's session. | staff (same gate as `/registry/`). |
| POST   | `/api/v1/session/touch/`        | Re-stamps the session, extending `expires_at`. Idempotent. CSRF required. | staff. |

Both endpoints are **optional** — the package only mounts them when
`DJANGO_ADMIN_REACT["SESSION_WARNING_SECONDS"]` is set to a positive
integer. Default unset → both endpoints 404 and the SPA shows the
re-login modal at expiry without prior warning.

When enabled, the SPA polls `GET /api/v1/session/` no more than
once per minute, and at `expires_at - SESSION_WARNING_SECONDS`
shows a toast inviting the user to "Stay signed in" →
`POST /api/v1/session/touch/`. Implementation slot tracked at
[#93](https://github.com/MartinCastroAlvarez/django-admin-react/issues/93)
(reserves the `session/` URL path against consumer app-name
collision).

### 10.3 What the package never does

- Modify `SESSION_COOKIE_AGE` or any `SESSION_COOKIE_*` setting at
  runtime. The consumer's Django settings are authoritative.
- Issue a new session cookie outside of Django's standard login
  flow. `/api/v1/session/touch/` only updates `request.session`'s
  expiry; it does not create a session.
- Echo the user's `?next=` parameter into any response body or
  header without Django's `url_has_allowed_host_and_scheme`
  validation upstream.

### 10.4 Cross-references

- Wire-shape detection: §6.1 above (landed in PR #95).
- SPA UX flow (modal mechanics): [`docs/ux/states.md`](ux/states.md) §3.5.
- Acceptance criteria: [`ACCEPTANCE.md`](../ACCEPTANCE.md) §2.7 N-5
  (modal flow) + N-6 (warning toast).
- Security posture: [`SECURITY.md`](../SECURITY.md) §4.1
  (Authentication), §4.6 (Session, CSRF, cookies).
