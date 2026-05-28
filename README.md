# django-admin-react

A drop-in **React single-page admin** for any Django 5+ project. Same
`pip install`, same `INSTALLED_APPS`, same `urls.py include()` — and
your `ModelAdmin` classes drive everything. No React code on your side.

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django.contrib.admin",
    "django_admin_react",   # the React SPA — includes the JSON API for you
]

# urls.py
urlpatterns = [
    path("admin/",       admin.site.urls),
    path("admin-react/", include("django_admin_react.urls")),  # SPA + API in one include
]
```

**One `INSTALLED_APPS` line + one URL include is the entire integration.** `pip install django-admin-react` transitively pulls in the [JSON API](https://pypi.org/project/django-admin-rest-api/) and the [MCP adapter](https://pypi.org/project/django-admin-mcp-api/); `django_admin_react.urls` includes the API endpoints at `<mount>/api/v1/…`, so the SPA finds its wire surface with zero configuration. (Mount the API a second time at your own prefix only if a non-SPA client also needs it.)

> **Beta — v1.0.0.** Available on PyPI; the SPA + the API
> ([`django-admin-rest-api`](https://pypi.org/project/django-admin-rest-api/))
> + the MCP adapter
> ([`django-admin-mcp-api`](https://pypi.org/project/django-admin-mcp-api/))
> all share the v1 wire contract. Track progress on the
> [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
> and the [Issues list](https://github.com/MartinCastroAlvarez/django-admin-react/issues).

## Three repos, one product

The project is split into three independently-published, cross-referenced repos so each piece can be consumed on its own merits:

| Repo | PyPI | Role |
|---|---|---|
| **[`django-admin-rest-api`](https://github.com/MartinCastroAlvarez/django-admin-api)** | [`django-admin-rest-api`](https://pypi.org/project/django-admin-rest-api/) | The JSON REST API for the Django admin — same permissions, same `ModelAdmin`, no new features. The wire surface. |
| **`django-admin-react`** *(this repo)* | [`django-admin-react`](https://pypi.org/project/django-admin-react/) | The React SPA frontend. A **super-layer** that depends on `django-admin-rest-api` for every wire call. |
| **[`django-admin-mcp-api`](https://github.com/MartinCastroAlvarez/django-admin-mcp)** | [`django-admin-mcp-api`](https://pypi.org/project/django-admin-mcp-api/) | Wire-protocol-only **MCP** adapter (call, manifest, …) over `django-admin-rest-api` — lets agents reach the same `ModelAdmin`-driven REST surface, no new functionality / permissions / validation. |

The wire contract itself lives in the **API repo** (`docs/api-contract.md` there). This README is about the SPA. The migration from "self-contained" to the 3-repo split is tracked in [META #544](https://github.com/MartinCastroAlvarez/django-admin-react/issues/544).

---

## Why django-admin-react

The Django admin is a 20-year-old hypertext app: full-page reloads,
mid-2000s aesthetics, no real mobile support, no client-side state.
It is also the most powerful piece of Django: `ModelAdmin` already
encodes your permissions, querysets, forms, fieldsets, search,
ordering, and inlines.

`django-admin-react` keeps every line of `ModelAdmin` you already
have and replaces only the UI:

| What you write                       | What the React SPA does with it                                              |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| `list_display`                       | Renders columns in a virtualised, sortable, mobile-collapsing table.         |
| `search_fields`                      | Renders a search bar that hits `get_search_results` verbatim.                |
| `list_filter`                        | Renders a sidebar drawer (desktop) / bottom-sheet (mobile) + filter chips.   |
| `date_hierarchy`                     | Renders a year → month → day drill-down strip.                                |
| `list_editable` / `list_per_page`    | Renders inline-editable cells + paginated list with deep links.              |
| `actions`                            | Renders a bulk-actions menu wired to the same `ModelAdmin.actions`.          |
| `fieldsets` / `readonly_fields`      | Renders the detail form respecting groups + read-only rules.                 |
| `autocomplete_fields`                | Renders type-ahead pickers that hit `<model>/autocomplete/?q=…`.             |
| `inlines = [TabularInline, ...]`     | Renders inlines as tables / card stacks alongside the parent.                |
| `has_*_permission`                   | Hides Add / Save / Delete buttons accordingly; never invents a permission.   |
| `get_queryset(request)`              | Every list, search, and detail lookup starts here. Never `Model.objects.all()`. |

The SPA is **metadata-driven** — it learns your models, fields, and
permissions at runtime from `GET /api/v1/registry/`. Add a new
`ModelAdmin` and refresh; no rebuild, no codegen.

---

## Screenshots

Real captures of the **django-admin-react SPA** rendering the bundled
`examples/` apps — driven entirely by each app's `ModelAdmin`.
Captured **manually** against a local dev server (no Playwright / Cypress /
e2e tooling required).

| Sign in (package login)                            | Registry / home                                       |
| -------------------------------------------------- | ----------------------------------------------------- |
| ![Sign in](https://raw.githubusercontent.com/MartinCastroAlvarez/django-admin-react/main/docs/screenshots/01-spa-login.png)      | ![Registry](https://raw.githubusercontent.com/MartinCastroAlvarez/django-admin-react/main/docs/screenshots/02-spa-registry.png)     |

| List view (`list_display` + search)                     | Detail view                                          |
| ------------------------------------------------------- | ---------------------------------------------------- |
| ![List](https://raw.githubusercontent.com/MartinCastroAlvarez/django-admin-react/main/docs/screenshots/03-spa-list.png)               | ![Detail](https://raw.githubusercontent.com/MartinCastroAlvarez/django-admin-react/main/docs/screenshots/05-spa-detail.png)        |

| Mobile (375 px)                                            | API: `GET /api/v1/registry/`                               |
| ---------------------------------------------------------- | ---------------------------------------------------------- |
| ![Mobile](https://raw.githubusercontent.com/MartinCastroAlvarez/django-admin-react/main/docs/screenshots/04-spa-list-mobile.png)         | ![Registry JSON](https://raw.githubusercontent.com/MartinCastroAlvarez/django-admin-react/main/docs/screenshots/06-registry-api-json.png) |

Screenshots use deterministic synthetic fixtures (no real names,
emails, account numbers, or PII).

---

## Install

```bash
pip install django-admin-react
```

This pulls in the JSON API ([`django-admin-rest-api`](https://pypi.org/project/django-admin-rest-api/))
and the MCP adapter ([`django-admin-mcp-api`](https://pypi.org/project/django-admin-mcp-api/))
as transitive dependencies. The **two-line `INSTALLED_APPS` + one-line
URL include** at the top of this README is the *entire* integration.
Mount at any prefix you like — `/admin-react/`, `/staff/`,
`/back-office/` — just don't collide with `django.contrib.admin`'s
own mount.

Log in as a staff user → modern, Tailwind-styled SPA driven by your
existing `ModelAdmin` classes.

The wheel ships the **pre-built React bundle**. You do **not** need
Node, pnpm, or any frontend toolchain to install or run.

### Optional configuration

All settings are optional. Defaults shown:

```python
DJANGO_ADMIN_REACT = {
    "ADMIN_SITE": "django.contrib.admin.site",   # dotted path to AdminSite instance
    "DEFAULT_PAGE_SIZE": 25,    # fallback only; the list page size derives
                                # from ModelAdmin.list_per_page (Django parity).
    "MAX_PAGE_SIZE": 200,
    "ENABLE_PROFILING": False,

    # Branding — all optional. The defaults derive from your AdminSite
    # (site_header / site_title / site_logo), so if you already branded
    # the HTML admin you need nothing here. Rendered server-side into the
    # SPA shell, so title + favicon are present on first paint (no FOUC).
    "BRAND_TITLE": None,        # str | None — override for BOTH brand strings.
    "BRAND_LOGO_URL": None,     # str | None — favicon + sidebar logo;
                                # falls back to AdminSite.site_logo. Absolute
                                # URL or a path under your STATIC_URL.
    "PRIMARY_COLOR": "#2563eb", # accent for primary buttons, links, and
                                # active states. Hex only (validated);
                                # injected as the --dar-primary CSS var, so
                                # rebranding needs no React rebuild.

    # Auth + API mount
    "REACT_LOGIN": True,        # bool — React-rendered login is the default;
                                # the SPA shell is served to anonymous users
                                # and posts to /api/v1/login/. Set False to
                                # opt back into the legacy admin HTML login.
    "API_URL_PREFIX": None,     # str | None — point the SPA at a separately-
                                # mounted django-admin-rest-api (e.g.
                                # "/api/api/v1/"). Default None keeps the
                                # inline include the package ships today.
}
```

#### Branding (`BRAND_TITLE` + `BRAND_LOGO_URL`)

Both default to `None` and **derive from your `AdminSite`**, mirroring
Django admin — so if you already customised the HTML admin's branding,
you need no settings here at all.

**Sidebar header** resolution:

1. `DJANGO_ADMIN_REACT["BRAND_TITLE"]` — explicit override.
2. `<your AdminSite>.site_header` — reused automatically.
3. `"Django Admin"` — last-resort fallback.

**Browser-tab `<title>`** resolution (Django uses `site_title` for the
tab, `site_header` for the on-page header):

1. `DJANGO_ADMIN_REACT["BRAND_TITLE"]` — explicit override.
2. `<your AdminSite>.site_title` — Django's tab-title source.
3. `<your AdminSite>.site_header` — fallback.
4. `"Django Admin"` — last-resort fallback.

`BRAND_LOGO_URL` accepts either an absolute URL or a path the browser
can resolve under your `STATIC_URL`. When unset, a `site_logo` attribute
on your `AdminSite` is used (Django has no logo by default, so set it as
a constant on your custom site). It is used both as the favicon
(`<link rel="icon">` in the SPA shell) and as the small logo next to
the brand title in the sidebar.

```python
# settings.py
DJANGO_ADMIN_REACT = {
    "BRAND_TITLE":    "Acme",
    "BRAND_LOGO_URL": "/static/acme/logo.svg",
}
```

Both values are written into the SPA index template as standard
`<meta>` tags (`dar-brand-title`, `dar-brand-logo`); the React shell
reads them at boot, so the first paint already carries the consumer's
brand. No flash of the package's defaults.

### Requirements

- **Python**: 3.10+
- **Django**: 5.0, 5.1, 5.2, 6.0 (and any later 6.x)
- **Database**: anything Django supports — the package is ORM-only,
  no direct SQL.
- **Auth**: Django's built-in session + CSRF. Works with custom
  `AUTH_USER_MODEL`, custom `AUTHENTICATION_BACKENDS`, and custom
  `AdminSite.has_permission`.

### Production: static files (and media for file uploads)

The wheel ships the pre-built bundle under the package's `static/` and
serves it through `{% static %}`. With `DEBUG = True`, Django's
staticfiles app serves it automatically — nothing to do. **In
production** you collect + serve static files like any Django app:

```python
# settings.py
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"   # where collectstatic gathers files
```

```bash
python manage.py collectstatic --no-input
```

Then serve `STATIC_ROOT` from your web server / CDN — or let
[WhiteNoise](https://whitenoise.readthedocs.io/) do it:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # right after SecurityMiddleware
    # ...
]
```

> If the SPA shell loads but its JS/CSS 404 (blank page, console errors),
> this `collectstatic` step is what's missing.

**File / image fields.** Editing `FileField` / `ImageField` needs
Django's media settings:

```python
# settings.py
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Uploads go through your configured file storage
(`STORAGES["default"]` / `DEFAULT_FILE_STORAGE`); in production serve
`MEDIA_ROOT` from your web server or object storage as usual.

> ⚠️ **Serving user-uploaded media has security implications** (access-gating, stored-file XSS). See [`SECURITY.md` §9](SECURITY.md) before exposing `MEDIA_URL` in production — `FileField`/`ImageField` are writable.

### Running side-by-side with the legacy admin

A common rollout: keep `/admin/` on the legacy HTML admin, mount the
React SPA at `/admin-react/`, and migrate users at your own pace.
Both run off the same `ModelAdmin` registrations — there is no
duplicate state.

```python
urlpatterns = [
    path("admin/",        admin.site.urls),                          # legacy, unchanged
    path("admin-react/",  include("django_admin_react.urls")),       # SPA
]
```

---

## Extend without writing React

Everything below is **just `ModelAdmin`**. No JavaScript. No new
classes. The UI follows whatever your admin declares.

### Pick what columns appear on the list view

```python
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "status", "total", "issued_at")
```

### Make columns sortable

```python
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "status", "total", "issued_at")
    sortable_by  = ("issued_at", "total")        # everything else is fixed
```

### Add free-text search

```python
class InvoiceAdmin(admin.ModelAdmin):
    search_fields = ("number", "customer__name", "notes__icontains")
    # The SPA wires `?q=<term>` to `ModelAdmin.get_search_results` verbatim.
```

### Default ordering

```python
class InvoiceAdmin(admin.ModelAdmin):
    ordering = ("-issued_at",)
```

### Hide a field from the form

```python
class InvoiceAdmin(admin.ModelAdmin):
    exclude         = ("internal_audit_hash",)   # never reaches the SPA
    readonly_fields = ("total",)                 # rendered as read-only
```

The SPA respects `exclude` and `readonly_fields` exactly the way the
legacy admin does. Sensitive-named fields (`password`, `secret`,
`token`, `api_key`, `hash`, `private_key`, `session`, `nonce`, `salt`)
are filtered on top of those rules as defense-in-depth.

### Group fields into sections

```python
class InvoiceAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identity",  {"fields": ("number", "customer")}),
        ("Money",     {"fields": ("subtotal", "tax", "total")}),
        ("Lifecycle", {"fields": ("status", "issued_at", "paid_at")}),
        ("Internal",  {"fields": ("notes",), "classes": ("collapse",)}),
    )
```

### Surface filters in the sidebar

```python
class InvoiceAdmin(admin.ModelAdmin):
    list_filter = ("status", "issued_at", "customer")
    # Boolean / choices / FK / date / SimpleListFilter all supported.
```

### Drill down by date

```python
class InvoiceAdmin(admin.ModelAdmin):
    date_hierarchy = "issued_at"
    # SPA renders a year → month → day strip wired to ?year=&month=&day=
```

### Edit cells inline on the list view

```python
class InvoiceAdmin(admin.ModelAdmin):
    list_editable = ("status",)
    # SPA: click cell → input swap → blur/Enter saves via PATCH /<app>/<model>/bulk/
```

### Add custom admin actions

```python
class InvoiceAdmin(admin.ModelAdmin):
    actions = ["mark_paid"]

    @admin.action(description="Mark selected as paid")
    def mark_paid(self, request, queryset):
        queryset.update(status="paid", paid_at=timezone.now())
```

The SPA renders a bulk-actions menu and posts to the same
`ModelAdmin.actions` machinery — same signatures, same audit
trail.

### Per-row permission gating

```python
class InvoiceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.has_perm("billing.create_invoice")

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return request.user.has_perm("billing.change_invoice")
        return obj.owner_id == request.user.id   # row-level rule

    def has_delete_permission(self, request, obj=None):
        return False    # nobody deletes invoices

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("billing.view_invoice")
```

The SPA hides the **Add** / **Save** / **Delete** buttons automatically
based on these. UI never invents a permission; it asks `ModelAdmin`.

### Restrict the queryset

```python
class InvoiceAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)
```

The list view never sees rows the queryset excludes. **No
`Model.objects.all()` in the package** — every list, search, and
detail lookup starts at `ModelAdmin.get_queryset(request)`.

### Custom save hook

```python
class InvoiceAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.last_edited_by = request.user
        super().save_model(request, obj, form, change)
```

Writes always go through `ModelAdmin.get_form()` → `form.is_valid()`
→ `save_model()`. Signals, audit logs, and post-save hooks all fire
exactly like they do in `/admin/`.

### Use a custom `AdminSite`

```python
# myproject/admin.py
from django.contrib.admin import AdminSite

class StaffAdminSite(AdminSite):
    site_header = "Operations Console"
    site_title  = "Ops"
    index_title = "Welcome"

    def has_permission(self, request):
        return request.user.is_active and request.user.is_staff and \
               request.user.groups.filter(name="ops").exists()

staff_admin = StaffAdminSite(name="staff")

# myproject/settings.py
DJANGO_ADMIN_REACT = {
    "ADMIN_SITE": "myproject.admin.staff_admin",
}
```

The SPA inherits the custom site's permission gate and the
`ModelAdmin` registrations on that site — no parallel registry.

### Plug in custom field types

```python
# yourapp/admin_react.py
from django_admin_react.api.serializers import register_field_type
from yourapp.fields import MoneyField

register_field_type(MoneyField, vocab_type="decimal")
# SPA renders MoneyField with the built-in decimal widget; no React
# code required.
```

Coining a brand-new `vocab_type` (with a matching SPA widget) is an
**API-repo** concern — open the issue at
[`MartinCastroAlvarez/django-admin-api`](https://github.com/MartinCastroAlvarez/django-admin-api).

### Pre-built `get_*` overrides still work

`get_form`, `get_fieldsets`, `get_fields`, `get_exclude`,
`get_readonly_fields`, `get_search_results`, `get_list_display`,
`get_sortable_by`, `get_list_filter`, `get_actions` — all of them
are called by the SPA the same way the HTML admin calls them. If
you customised them for `/admin/`, the SPA already honours those
customisations.

---

## Feature status (alpha — currently `0.2.0a*` on PyPI)

The **backend** — the `ModelAdmin`-driven REST API — is the stable,
complete surface and the table below tracks it. The **React SPA** that
consumes it is in active development; to keep this README from drifting,
per-feature *SPA* (UI) status is **not** duplicated here — it is tracked
live in the [frontend implementation tracker (#160)](https://github.com/MartinCastroAlvarez/django-admin-react/issues/160)
and the [project board](https://github.com/users/MartinCastroAlvarez/projects/3).

| `ModelAdmin` surface                                   | Backend (REST API)                                              |
| ------------------------------------------------------ | --------------------------------------------------------------- |
| Registry / list / detail / create / update / delete    | ✅                                                              |
| `list_display`, `sortable_by`, `search_fields`         | ✅                                                              |
| `list_filter` (boolean / choice / FK / date / Simple)  | ✅                                                              |
| `date_hierarchy`                                       | ✅                                                              |
| `list_editable` + bulk PATCH                           | ✅                                                              |
| `actions` (custom + bulk runner)                       | ✅                                                              |
| `autocomplete_fields` / `raw_id_fields`                | ✅                                                              |
| `ManyToManyField` read + write                         | ✅                                                              |
| `inlines` (TabularInline / StackedInline) — read + write | ✅                                                            |
| `FileField` / `ImageField` — read                      | ✅                                                              |
| `FileField` / `ImageField` — multipart upload          | 🟡 [#241](https://github.com/MartinCastroAlvarez/django-admin-react/issues/241) |
| `JSONField` / `ArrayField` / range — read              | ✅                                                              |
| range fields — write coercion                          | 🟡 [#238](https://github.com/MartinCastroAlvarez/django-admin-react/issues/238) |
| `register_field_type` + per-model extension hook       | ✅                                                              |
| React login / logout (Django session + CSRF)           | ✅                                                              |
| Password set / change (`UserAdmin` parity)             | ✅                                                              |
| Session-expiry re-login contract                       | ✅                                                              |
| OpenAPI 3.1 schema at `/api/v1/schema/`                | ✅                                                              |
| PWA manifest + service worker (cache-purge on logout)  | ✅                                                              |

✅ = shipped in the current alpha. 🟡 = not yet built (tracked). This
column is the **backend** capability only — for which surfaces the React
UI renders today, see the [frontend tracker (#160)](https://github.com/MartinCastroAlvarez/django-admin-react/issues/160).

---

## The API surface

The SPA is a thin client over a small, closed REST surface. You can
also use these endpoints from any HTTP client (curl, your own
frontend, a script).

| Method  | Path                                              | Purpose                                                                       |
| ------- | ------------------------------------------------- | ----------------------------------------------------------------------------- |
| `GET`   | `/api/v1/registry/`                               | All apps + models the current user can see, with their permissions.           |
| `GET`   | `/api/v1/schema/`                                 | OpenAPI 3.1 schema for the envelopes + closed type vocabulary.                |
| `GET`   | `/api/v1/<app>/<model>/`                          | Paginated list. Honours `?search=`, `?ordering=`, `?page=`, `list_filter`.    |
| `POST`  | `/api/v1/<app>/<model>/`                          | Create. Runs `ModelAdmin.get_form()` + `form.is_valid()` + `save_model()`.    |
| `GET`   | `/api/v1/<app>/<model>/<pk>/`                     | Detail with serialised fields, `permissions`, `inlines`, `panels`.            |
| `PATCH` | `/api/v1/<app>/<model>/<pk>/`                     | Partial update. Same form pipeline as POST.                                   |
| `DELETE`| `/api/v1/<app>/<model>/<pk>/`                     | Hard delete via `ModelAdmin.delete_model()`.                                  |
| `PATCH` | `/api/v1/<app>/<model>/bulk/`                     | `list_editable` round-trip for multiple rows.                                 |
| `POST`  | `/api/v1/<app>/<model>/<action>/`                 | Invoke a registered `ModelAdmin.actions` entry on a queryset.                 |
| `GET`   | `/api/v1/<app>/<model>/autocomplete/?q=…`         | `autocomplete_fields` lookup. Permission-gated on the **target** model.       |

Every endpoint is **staff-only by default** (or whatever
`AdminSite.has_permission` returns), CSRF-required on unsafe
methods, and emits `Cache-Control: no-store`. Full wire contract
lives in the API repo:
[`MartinCastroAlvarez/django-admin-api`](https://github.com/MartinCastroAlvarez/django-admin-api).

---

## Examples

Six runnable example projects ship with the repo under
[`examples/`](examples/):

| Project    | What it exercises                                                                                  |
| ---------- | -------------------------------------------------------------------------------------------------- |
| `library/` | `Author`, `Book`, `Genre` — basic CRUD, FKs, M2M, `search_fields`, `list_filter`.                  |
| `fintech/` | `Account`, `Transaction` — permissions, queryset narrowing, custom actions.                        |
| `blog/`    | `Post`, `Tag`, `Comment` — `list_editable`, `inlines`, `date_hierarchy`.                           |
| `ecommerce/` | `Product`, `Order`, `LineItem` — fieldsets, readonly, `register_field_type` for `MoneyField`.    |
| `hr/`      | `Employee`, `Department` — `autocomplete_fields`, `raw_id_fields`, organisational filters.         |
| `project/` | Glue project that mounts every example app for an end-to-end demo.                                 |

Boot any of them with:

```bash
cd examples/project
python manage.py migrate
python manage.py loaddata seed
python manage.py runserver
# → http://127.0.0.1:8000/admin/    (legacy admin)
# → http://127.0.0.1:8000/admin-react/  (the React SPA)
```

---

## What you get

- **Plug-and-play**: works with any `ModelAdmin` you already have.
- **Shared auth**: Django sessions, CSRF, staff permissions. No new
  user model, no parallel permission system.
- **Responsive, modern UI**: React + Tailwind + React Query, served
  as a single bundle from `django_admin_react/static/admin_react/`.
- **Extensible by editing `ModelAdmin`**, not React. Per-model SPA
  extension hooks for the cases that genuinely need them.
- **Configurable URL prefix** — `/admin/`, `/admin-react/`, anywhere.
- **Conservative & secure-by-default** — never exposes models the
  admin doesn't already expose; never writes fields the admin form
  excludes; CSRF on every unsafe method; `Cache-Control: no-store`
  on every API response; sensitive-name denylist on top of the
  admin's own `exclude` rules.
- **Boring + auditable** — no parallel permission system, no
  client-side workarounds for backend permissions, conservative
  serializer with `str()` fallback.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Security

Please report security issues privately through GitHub's Private
Vulnerability Reporting on the repository (Security → Advisories).
See [`SECURITY.md`](SECURITY.md). Do **not** open a public issue.

## Contributing

Open an [Issue](https://github.com/MartinCastroAlvarez/django-admin-react/issues/new)
or a [Discussion](https://github.com/MartinCastroAlvarez/django-admin-react/discussions)
before sending a PR for anything non-trivial. **API-side contributions** (any
`/api/v1/...` endpoint, the wire contract, permission gates, serializer
denylist) go to [`MartinCastroAlvarez/django-admin-api`](https://github.com/MartinCastroAlvarez/django-admin-api)
— this repo owns only the **React SPA super-layer** on top.
