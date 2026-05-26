# Architecture

`django-admin-react` is a Django package that exposes a stable, conservative
REST API on top of `django.contrib.admin` and ships a pre-built React
single-page application that consumes it. The Django ModelAdmin is the **only
source of truth** for permissions, querysets, forms, and field configuration.

> This document is the architectural contract. Any change that conflicts with
> it must update this file in the same PR and be recorded in
> [`docs/agents/decisions.md`](docs/agents/decisions.md).

---

## 1. Goals (v1)

1. **Plug-and-play replacement** for `django.contrib.admin`'s HTML views.
2. **Single-page, responsive** React UI built with Tailwind.
3. **Shared authentication** with `django.contrib.admin` (Django session +
   CSRF). Staff-only by default. The package never invents its own user or
   permission model.
4. **Extensible without writing React**. Developers extend the Django
   `ModelAdmin` they already write; the UI reflects the changes
   automatically.
5. **Configurable URL mount point**. The consumer chooses where the package
   is served (e.g., `/admin/`, `/admin-react/`, `/staff/`).
6. **Open-source, PyPI-publishable**, security-audited.

Explicit non-goals for v1: inlines, custom admin actions, bulk actions,
custom admin widgets, complex filters, autocomplete fields, `raw_id_fields`,
and a React-side extension API. The
[Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
tracks each deferred item by Phase.

---

## 2. High-level shape

```
┌───────────────────────────────┐         ┌─────────────────────────────┐
│  Browser (React SPA)          │         │  Consumer Django project    │
│  - React + React Router       │  HTTPS  │  - urls.py includes         │
│  - React Query                │  ◄────► │    django_admin_react.urls  │
│  - Tailwind                   │ session │  - settings has the package │
│  - Reads only API metadata    │ + CSRF  │  - django.contrib.admin is  │
└──────────────▲────────────────┘         │    still the source of      │
               │                          │    truth for permissions    │
               │                          └──────────────┬──────────────┘
               │                                         │
               │ static index.html + JS/CSS              │
               │                                         │
┌──────────────┴────────────────┐         ┌──────────────▼──────────────┐
│  django_admin_react (pkg)     │         │  admin.site._registry       │
│  - urls.py (mountable)        │ reads   │  ModelAdmin instances       │
│  - api/v1/* DRF-style views   │ ◄────── │  (the consumer's)           │
│  - templates/admin_react/...  │         │                             │
│  - static/admin_react/...     │         │                             │
└───────────────────────────────┘         └─────────────────────────────┘
```

The package never imports the consumer's models directly. It works
exclusively through Django's `AdminSite._registry` to discover models and
through each `ModelAdmin` instance's public methods to act on them.

---

## 3. Repository layout

```
django-admin-react/
├── django_admin_react/          # The Python package (PyPI artifact)
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py                  # Mountable. Splits api/ and SPA/ subroutes.
│   ├── views.py                 # Index view (serves React index.html).
│   ├── api/
│   │   ├── __init__.py
│   │   ├── permissions.py       # IsStaffUser, model-level checks
│   │   ├── registry.py          # AdminSite introspection helpers
│   │   ├── serializers.py       # Conservative field serialization
│   │   ├── urls.py
│   │   └── views/
│   │       ├── registry.py      # GET /api/v1/registry/
│   │       ├── list.py          # GET /api/v1/{app}/{model}/
│   │       ├── detail.py        # GET   /api/v1/{app}/{model}/{pk}/
│   │       ├── create.py        # POST  /api/v1/{app}/{model}/
│   │       ├── update.py        # PATCH /api/v1/{app}/{model}/{pk}/
│   │       └── delete.py        # DELETE
│   ├── conf.py                  # settings.DJANGO_ADMIN_REACT loader
│   ├── templates/admin_react/index.html
│   └── static/admin_react/      # Compiled React bundle drops here
│
├── frontend/                    # pnpm workspace (not shipped via PyPI)
│   ├── pnpm-workspace.yaml
│   ├── package.json
│   └── packages/
│       ├── shell/               # App shell, router, auth boundary
│       ├── ui/                  # Generic, reusable, props-driven primitives
│       ├── api/                 # React Query hooks; typed API client
│       ├── data/                # Context providers + localStorage cache;
│       │                        # the only data layer UI packages talk to
│       ├── list/                # List-view components
│       ├── details/             # Detail/edit/create components
│       └── models/              # Model navigation, registry browsing
│
├── examples/                    # Demo Django projects, not packaged
│   ├── fintech/                 # Account, Transaction, Statement, ...
│   ├── library/                 # Author, Book, Loan, ...
│   ├── blog/                    # Post, Comment, Tag, ...
│   └── shared_project/          # Settings/urls glue that mounts the lib
│
├── tests/                       # Pytest suite for the Python package
│   ├── conftest.py
│   ├── test_project/            # Minimal Django project for tests
│   └── ...
│
├── docs/                        # Long-form documentation
│   ├── api-contract.md
│   ├── installation.md
│   └── agents/
│       ├── decisions.md
│       └── open-questions.md
│
├── ARCHITECTURE.md              # ← you are here
├── SECURITY.md
├── CONTRIBUTING.md
├── CLAUDE.md                    # Required reading for AI agents
├── README.md
├── LICENSE
└── pyproject.toml               # Poetry-managed
```

Live status / backlog / coordination lives on GitHub (Issues, the
[Project board](https://github.com/users/MartinCastroAlvarez/projects/3),
Discussions, PR review comments), not in committed markdown.

Every folder above has its own `README.md` describing its purpose and what
belongs there. This is enforced in [`CLAUDE.md`](CLAUDE.md).

---

## 4. Backend design

### 4.1 The ModelAdmin contract

For every API operation, the backend resolves the target `ModelAdmin`
through `admin.site._registry` and delegates:

| Operation        | Methods consulted on `ModelAdmin`                                                  |
| ---------------- | ----------------------------------------------------------------------------------- |
| List models      | `admin.site._registry` (and `has_module_permission`, `has_view_permission`)        |
| List objects     | `get_queryset(request)`, `get_search_results(...)`, `get_list_display(request)`    |
| Detail           | `get_queryset(request)`, `has_view_permission(request, obj)`, `get_form(request, obj)` |
| Create           | `has_add_permission(request)`, `get_form(request)`, `save_model(...)`              |
| Update           | `has_change_permission(request, obj)`, `get_form(request, obj)`, `save_model(...)` |
| Delete           | `has_delete_permission(request, obj)`, `delete_model(request, obj)`                |
| Field visibility | `get_fields`, `get_readonly_fields`, `get_exclude`, `get_fieldsets`                |

The package **never** calls `Model.objects.all()` directly. The starting
queryset always comes from `ModelAdmin.get_queryset(request)`.

The package **never** trusts a client-provided `app_label`/`model_name`
without round-tripping through `admin.site._registry`. Unregistered models
return `404`.

### 4.2 Authentication & authorization

- Reuses Django's session middleware. If a user is logged into
  `django.contrib.admin`, they are logged into the React SPA at the same
  cookie scope.
- CSRF enforcement is **on** for all unsafe methods (`POST`, `PATCH`,
  `PUT`, `DELETE`).
- Default access policy: `request.user.is_active and request.user.is_staff`.
- Per-model and per-object access is **never** decided by the package; it is
  always the answer of the appropriate `has_*_permission` on the
  `ModelAdmin`.
- If a consumer customizes their `AdminSite.has_permission()` (e.g., to allow
  non-staff users), this package follows that customization — it does not
  claim its own access policy beyond the staff default fallback.

### 4.3 Serialization rules

Conservative, list in [`SECURITY.md`](SECURITY.md) and codified in
`api/serializers.py`:

- Pass-through types: `str`, `int`, `float`, `bool`, `None`,
  `Decimal` (as string), `UUID` (as string), `date` (ISO), `datetime` (ISO
  with timezone).
- `ForeignKey` → `{ "id": ..., "label": str(obj) }`.
- `ManyToMany` — out of scope for v1; surface as `null` with a flag
  `"unsupported": true`. (Decision logged in
  `docs/agents/decisions.md`.)
- Callable `list_display` values are invoked with the object and serialized
  via `str(value)`.
- Anything else falls back to `str(value)` rather than crashing.
- Passwords, secrets, tokens, API keys, hashed fields, and any field listed
  in `ModelAdmin.exclude`/`get_exclude` are **never** serialized.

### 4.4 Write path

- Creates and updates **must** go through `ModelAdmin.get_form()`.
- `PATCH` is implemented as: load the bound form's initial data from the
  existing object, merge the incoming payload, validate, then save through
  `ModelAdmin.save_model(...)`.
- `DELETE` calls `ModelAdmin.delete_model(request, obj)`, never
  `obj.delete()`.
- The package refuses to write fields that the admin form excludes,
  marks readonly, or otherwise hides — even if the client provides them.

### 4.5 URL mounting

`django_admin_react.urls` is a standard `urlpatterns` list that the consumer
includes wherever they like:

```python
# consumer project urls.py
from django.urls import include, path

urlpatterns = [
    path("admin-react/", include("django_admin_react.urls")),
]
```

The package does **not** hardcode `/admin-react/`. Internally it derives all
links from `request.path` and `reverse()`, so the SPA works at any mount
point. The mount point is exposed to the SPA via a `<meta>` tag in
`index.html` so the React client knows where its API lives.

### 4.6 Settings

A single optional dict `settings.DJANGO_ADMIN_REACT` controls package
behaviour. v1 keys (all optional):

```python
DJANGO_ADMIN_REACT = {
    "ADMIN_SITE": "django.contrib.admin.site",   # dotted path; default = the
                                                  # global admin site
    "DEFAULT_PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 200,
    "ENABLE_PROFILING": False,

    # Branding (consumer-facing SPA shell)
    "BRAND_TITLE":    None,   # str | None — sidebar header + tab title.
                              # None → falls back to ADMIN_SITE.site_header,
                              # then to "Django Admin".
    "BRAND_LOGO_URL": None,   # str | None — favicon + sidebar logo.
                              # Absolute URL or a path under STATIC_URL.
}
```

The package reads these via `django_admin_react/conf.py` (a thin lazy
wrapper). Nothing in the package may read `settings.DJANGO_ADMIN_REACT`
directly.

`BRAND_TITLE` and `BRAND_LOGO_URL` are rendered server-side into the
SPA index template (`templates/admin_react/index.html`) as
`<meta name="dar-brand-title">` and `<meta name="dar-brand-logo">`.
The React shell reads them at boot — first paint already carries the
consumer's brand; no FOUC against the package defaults. They are
plain text / URL; no markup is interpolated.

---

## 5. Frontend design

### 5.1 Monorepo layout

The frontend is a `pnpm` workspace. Packages are intentionally small and
single-purpose:

- **`@dar/ui`** — Tailwind-styled primitives (Button, Input, Select, Table,
  Pagination, Toast, FormField, Skeleton, Empty, Error). No business logic.
  No knowledge of Django, models, or the API.
- **`@dar/api`** — Thin REST client + React Query hooks
  (`useRegistry`, `useObjectList`, `useObject`, `useCreateObject`,
  `useUpdateObject`, `useDeleteObject`). One source of typing for everything
  the API returns. **UI packages never import `@dar/api` directly** — they
  go through `@dar/data` (see below).
- **`@dar/data`** — The single source of truth UI components read from.
  Implemented as React Context providers (`RegistryProvider`,
  `ObjectListProvider`, `ObjectProvider`). Each provider:
  - On mount, **hydrates synchronously from `localStorage`** so the UI has
    something to render on first paint, even offline.
  - Calls into `@dar/api` (React Query) to fetch the canonical server
    state; once it arrives, reconciles the local cache and dispatches a
    re-render.
  - **Debounces user-initiated mutations** (a small configurable window;
    default 300ms for field edits, 0ms for explicit submit/delete) so the
    UI feels responsive without flooding the backend with PATCHes.
  - Writes through to `@dar/api` mutations on debounce flush; on server
    rejection, rolls back the local cache and surfaces a toast via
    `@dar/ui`.
  - Owns conflict resolution for concurrent edits in v1.x; in v1 it
    uses "last write wins" with a warning.
  This is the **only** layer UI packages (`@dar/list`, `@dar/details`,
  `@dar/models`) talk to. They never import React Query or `@dar/api`
  directly. This rule keeps the data-flow boundary explicit and lets us
  swap the cache backend later without touching UI code.
- **`@dar/list`** — Generic list page. Reads metadata from `@dar/data`,
  renders headers from `list_display`, wires search/pagination.
- **`@dar/details`** — Generic detail/create/update page. Renders a form
  from the field metadata returned by `@dar/data`.
- **`@dar/models`** — Sidebar/registry navigation. Lists apps and models the
  current user can view, sourced from `@dar/data`.
- **`@dar/web`** — App entry point, router, auth boundary, layout, theme
  bootstrap. This is what gets built into the Django package's `static/`.

### 5.2 Genericity rule

No frontend package may know about `Account`, `Book`, `Transaction`, or any
example model. The UI is driven entirely by API metadata. If something
cannot be rendered generically from the metadata the backend returns, the
metadata is incomplete — fix the backend, not the frontend.

### 5.2a Data layering rule

There is exactly one data path inside the SPA:

```
@dar/api  ◄── network ──►  Django REST endpoints
   ▲
   │ (only @dar/data may import @dar/api)
   ▼
@dar/data  ◄── React Context ──►  @dar/list, @dar/details, @dar/models, @dar/web
```

- UI packages must read from `@dar/data` hooks (`useRegistry`,
  `useObjectList`, `useObject`, `useMutateObject`). They must not
  `import "@dar/api"` directly.
- `@dar/data` is the persistence + reconciliation layer: localStorage on
  first paint, React Query in the background, debounced writes.
- A misuse is a CI-failing lint rule (added in PR #6).

### 5.3 Tailwind & theming

- The package ships a `tailwind.config.js` with a minimal, modern, neutral
  palette and CSS-variable-backed colors for trivial recoloring.
- Consumers can extend it via their own `tailwind.config.js`; this is
  documented in `docs/installation.md`.
- **Partial replacement is supported** (e.g., override `colors`, `fontFamily`,
  `spacing`).
- **Full replacement of the config is not a v1 goal** — it would mean every
  component is on a yet-undefined contract. We support theming through
  CSS variables, which is enough for ~90% of branding needs without
  rebuilding the bundle.
- An "extend the bundle yourself" escape hatch is documented for advanced
  users who want to rebuild from source against a custom Tailwind config.

### 5.4 Build & ship

- `pnpm --filter @dar/web build` produces a `dist/` with `index.html`,
  hashed JS, and hashed CSS.
- A `make build-frontend` (or `poetry run dar-build`) command copies the
  artifact into `django_admin_react/static/admin_react/` and
  `django_admin_react/templates/admin_react/index.html`.
- The Python package on PyPI ships the **pre-built** assets so consumers do
  not need Node to install it.

---

## 6. Permissions surfaced to the UI

For every model and every object the UI receives, the API returns a
`permissions` object reflecting the `ModelAdmin` answer:

```json
{
  "view":   true,
  "add":    true,
  "change": true,
  "delete": false
}
```

The React app uses these booleans to hide/disable buttons. Even if the
client tries to call a forbidden endpoint anyway, the backend re-checks via
`has_*_permission` and responds `403`. The UI is a courtesy; the backend is
the gate.

---

## 7. Versioning & stability

- The API namespace is `api/v1/`. Breaking changes require a new namespace.
- The SPA always targets the API namespace it was built against. Mismatched
  versions return a clear error rather than rendering broken pages.
- Python package version follows SemVer, tracked in `pyproject.toml`.

---

## 8. Out-of-scope (and why)

- **Inlines** — require a recursive form contract. Deferred to v1.x.
- **Custom admin actions** — need a safe whitelist mechanism. Deferred.
- **Bulk actions** — partially overlaps with custom actions. Deferred.
- **Custom widgets** — would force a widget-registry contract between
  backend and frontend. Deferred.
- **Autocomplete / raw_id** — depend on cross-model permissions and
  efficient search; deferred until basic flows are stable.
- **A React-side extension API** — explicitly avoided: extending should
  always happen by editing `ModelAdmin` on the Django side. If users need
  React extensibility later, we will design the contract carefully rather
  than ad-hoc.

See the
[Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
for the sequencing of in-scope work.
