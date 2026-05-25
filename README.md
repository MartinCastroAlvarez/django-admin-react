# django-admin-react

A Django package that replaces the stock `django.contrib.admin` HTML
views with a responsive, single-page React UI — **without** requiring
you to write any React.

```
pip install django-admin-react
```

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django_admin_react",
    # ... your apps
]

# urls.py
from django.urls import include, path
urlpatterns = [
    path("admin/",        include("django_admin_react.urls")),  # or wherever
    # path("admin-react/", include("django_admin_react.urls")), # any prefix is fine
]
```

That's it. Log into the admin and you'll see a modern, Tailwind-styled
SPA driven by your existing `ModelAdmin` classes.

---

## What you get

- **Plug-and-play**: works with any `ModelAdmin` you already have.
- **Shared auth**: uses Django's existing sessions, CSRF, and staff
  permissions. No new user model, no new permission system.
- **Responsive, modern UI**: built with React, Tailwind, React Query.
- **Extensible by editing `ModelAdmin`, not React**. Change
  `has_add_permission` server-side and the Add button disappears
  client-side. No JS required.
- **Configurable mount point**: serve at `/admin/`, `/admin-react/`,
  `/staff/`, anywhere.
- **Conservative & secure-by-default**: never exposes models the admin
  doesn't already expose; never writes fields the admin form
  excludes.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the design contract.

---

## Status

**Pre-alpha**. Not yet on PyPI. APIs, contracts, and the React bundle
are all subject to change. See [`PLAN.md`](PLAN.md) for the roadmap and
the in-scope / out-of-scope list.

---

## Documentation map

This README is intentionally lean. Detailed docs live in dedicated
files:

| Doc                                                | Topic                                          |
| -------------------------------------------------- | ---------------------------------------------- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md)               | System design, contracts, invariants           |
| [`PLAN.md`](PLAN.md)                               | What's in v1, sequenced PR plan, risks         |
| [`SECURITY.md`](SECURITY.md)                       | Threat model, guarantees, required tests       |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)               | Dev workflow, code style, tests, releases      |
| [`CLAUDE.md`](CLAUDE.md)                           | Rules for AI agents working on this repo       |
| [`docs/api-contract.md`](docs/api-contract.md)     | Full API spec (endpoints, payloads, errors)    |
| [`docs/agents/decisions.md`](docs/agents/decisions.md) | Durable architectural decisions log         |
| [`docs/agents/open-questions.md`](docs/agents/open-questions.md) | Unresolved questions                |
| [`docs/agents/changelog.md`](docs/agents/changelog.md) | Running log of meaningful repo changes      |
| [`forum/`](forum/)                                 | Ephemeral coordination between AI agents       |
| [`examples/README.md`](examples/README.md)         | How to run the demo Django apps                |
| [`tests/README.md`](tests/README.md)               | Test suite layout                              |
| [`django_admin_react/README.md`](django_admin_react/README.md) | Python package internals             |
| [`frontend/README.md`](frontend/README.md)         | React monorepo internals                       |

---

## Quickstart for consumers (preview)

### 1. Install

```bash
pip install django-admin-react
```

(Currently, install from source — see [`CONTRIBUTING.md`](CONTRIBUTING.md).)

### 2. Add to `INSTALLED_APPS`

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_admin_react",
    # ... your apps
]
```

### 3. Mount the URLs wherever you want

```python
# urls.py
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Option A: replace the default admin entirely
    path("admin/", include("django_admin_react.urls")),

    # Option B: keep the old admin and mount the React UI alongside
    path("admin/legacy/", admin.site.urls),
    path("admin/",        include("django_admin_react.urls")),

    # Option C: any prefix you like
    # path("staff/",       include("django_admin_react.urls")),
]
```

### 4. Optional: configure

All settings are optional. Defaults shown:

```python
# settings.py
DJANGO_ADMIN_REACT = {
    "ADMIN_SITE": "django.contrib.admin.site",  # dotted path
    "DEFAULT_PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 200,
    "ENABLE_PROFILING": False,
}
```

### 5. Extend without writing React

Just edit your `ModelAdmin` classes — the UI follows.

```python
# yourapp/admin.py
from django.contrib import admin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "total", "issued_at")
    search_fields = ("number", "customer__name")
    readonly_fields = ("total",)        # ← UI hides the input
    list_filter = ("status",)           # ← UI surfaces the filter (v1.1+)

    def has_add_permission(self, request):
        return request.user.has_perm("billing.create_invoice")  # ← UI hides Add button
```

---

## Tailwind / theming

The package ships a minimalist, modern Tailwind config with CSS-variable
backed colors so light customization doesn't require rebuilding the
bundle. Full Tailwind config replacement is **not** supported in v1; see
[`ARCHITECTURE.md`](ARCHITECTURE.md) §5.3 for the rationale.

For deeper customization, rebuild the bundle from source against your
own Tailwind config — see [`frontend/README.md`](frontend/README.md).

---

## License

MIT — see [`LICENSE`](LICENSE).

---

## Security

Please report security issues privately. See
[`SECURITY.md`](SECURITY.md) §4 for the process. Do **not** open a
public GitHub issue.

---

## Contributing

Both humans and AI agents are welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md). If you're an AI agent,
[`CLAUDE.md`](CLAUDE.md) is required reading.
