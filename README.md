# django-admin-react

A drop-in **React single-page admin** for any Django 5+ project. Same
`pip install`, same `INSTALLED_APPS`, same `urls.py include()` — and
your `ModelAdmin` classes drive everything. No React code on your side.

> **Pre-alpha.** Not yet on PyPI. Install from source today (see below);
> a `pip install django-admin-react` release will follow. Track progress
> in [`PROGRESS.md`](PROGRESS.md).

---

## Install in your Django project

### Option A — once on PyPI (planned)

```bash
pip install django-admin-react
```

```python
# settings.py
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_admin_react",   # ← add this
    # ... your own apps
]
```

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("admin/", include("django_admin_react.urls")),
    # any prefix is fine:
    # path("admin-react/", include("django_admin_react.urls")),
    # path("staff/",       include("django_admin_react.urls")),
]
```

That is the entire integration. Log in as a staff user → modern,
Tailwind-styled SPA driven by your existing `ModelAdmin` classes.

The wheel ships the **pre-built React bundle**. You do **not** need
Node, pnpm, or any frontend toolchain to install or run.

### Option B — install from source (today)

```bash
git clone https://github.com/MartinCastroAlvarez/django-admin-react.git
cd django-admin-react
./scripts/build.sh              # builds the SPA + Python wheel
pip install dist/*.whl          # install into your venv
```

Then wire it into your project as in Option A.

### Optional configuration

All settings are optional. Defaults shown:

```python
DJANGO_ADMIN_REACT = {
    "ADMIN_SITE": "django.contrib.admin.site",   # dotted path
    "DEFAULT_PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 200,
    "ENABLE_PROFILING": False,
}
```

---

## Extend without writing React

Just edit your `ModelAdmin` — the UI follows. No JS required.

```python
# yourapp/admin.py
from django.contrib import admin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "total", "issued_at")
    search_fields = ("number", "customer__name")
    readonly_fields = ("total",)            # ← UI hides the input
    list_filter = ("status",)               # ← UI surfaces the filter

    def has_add_permission(self, request):
        return request.user.has_perm("billing.create_invoice")
        #                                                     ↑
        # UI hides the Add button automatically when this returns False.
```

Permissions, querysets, search, validation — all your `ModelAdmin`'s
answers, surfaced verbatim in the React UI. The package never invents
its own permission model.

---

## Screenshots

> The React bundle is wired in PR #6/#7. While the SPA is being built,
> the screenshots below are ASCII mockups that match the API contract
> exactly. They will be replaced with real screenshots once the UI is
> usable. See [`PROGRESS.md`](PROGRESS.md) for live status.

**Model registry / sidebar** — sourced from `GET /api/v1/registry/`:

```
┌───────────────────────────────┐ ┌─────────────────────────────────┐
│ django-admin-react            │ │  Welcome, Alice                │
│  • Auth                       │ │                                 │
│      Users                    │ │  Apps you can manage:           │
│      Groups                   │ │   ▸ Auth        (2 models)      │
│  • Fintech                    │ │   ▸ Fintech     (4 models)      │
│      Accounts                 │ │   ▸ Library     (5 models)      │
│      Transactions             │ │                                 │
│      Statements               │ │  Recent activity: —             │
│      Cards                    │ │                                 │
│  • Library                    │ │                                 │
│      Authors                  │ │                                 │
│      Books                    │ │                                 │
│      Loans                    │ │                                 │
└───────────────────────────────┘ └─────────────────────────────────┘
```

**Object list** — list_display columns + search + pagination,
sourced from `GET /api/v1/<app>/<model>/`:

```
┌─────────────────────────────────────────────────────────────────┐
│  Fintech / Accounts                              [ + Add new ]  │
│  ┌─────────────────────────────────────┐  ┌──────────────────┐  │
│  │ 🔎 Search by name or IBAN…          │  │ Filter ▾         │  │
│  └─────────────────────────────────────┘  └──────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Name                  Balance     Active   Owner         │   │
│  │ ───────────────────────────────────────────────────────  │   │
│  │ Checking — Alice      1 023.45    ✓        alice         │   │
│  │ Savings — Alice         512.00    ✓        alice         │   │
│  │ Investing — Bob       8 900.10    ✓        bob           │   │
│  └──────────────────────────────────────────────────────────┘   │
│  Page 1 of 6 · 137 results                ⟨ Prev    Next ⟩      │
└─────────────────────────────────────────────────────────────────┘
```

**Detail / edit** — fields built from `ModelAdmin.get_form()`,
sourced from `GET /api/v1/<app>/<model>/<pk>/`:

```
┌─────────────────────────────────────────────────────────────────┐
│  Fintech / Accounts / Checking — Alice          [ Save ] [ … ]  │
│                                                                 │
│  Name        [ Checking — Alice                              ]  │
│  Balance     [ 1023.45                       ] (read-only)      │
│  Active      [✓]                                                │
│  Owner       [ alice ▾ ]                                        │
│                                                                 │
│  Statements  ⚠ unsupported field (M2M) — coming in v1.x         │
│                                                                 │
│  ───────────────────────────────────────────────────────────    │
│  [ Delete ]                                                     │
└─────────────────────────────────────────────────────────────────┘
```

The "Delete" button hides automatically if the user's
`has_delete_permission` is false. The "unsupported" stub appears
verbatim for M2M fields until v1.x.

---

## What you get

- **Plug-and-play**: works with any `ModelAdmin` you already have.
- **Shared auth**: Django sessions, CSRF, staff permissions. No new
  user model, no parallel permission system.
- **Responsive, modern UI**: React + Tailwind + React Query, served
  as a single bundle from `django_admin_react/static/admin_react/`.
- **Extensible by editing `ModelAdmin`**, not React.
- **Configurable URL prefix** — `/admin/`, `/admin-react/`, anywhere.
- **Conservative & secure-by-default** — never exposes models the
  admin doesn't already expose; never writes fields the admin form
  excludes; CSRF on every unsafe method.
- **Boring + auditable** — no parallel permission system, no
  client-side workarounds for backend permissions, conservative
  serializer with `str()` fallback.

---

## Documentation map

| Doc                                                             | Topic                                       |
| ---------------------------------------------------------------- | -------------------------------------------- |
| [`PROGRESS.md`](PROGRESS.md)                                     | Live status of merged PRs / what's coming   |
| [`ARCHITECTURE.md`](ARCHITECTURE.md)                             | Design contract                              |
| [`PLAN.md`](PLAN.md)                                             | v1 scope, PR sequence, risks                 |
| [`SECURITY.md`](SECURITY.md)                                     | Threat model, guarantees, required tests     |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)                             | Dev workflow                                 |
| [`CLAUDE.md`](CLAUDE.md)                                         | Rules for AI contributors                    |
| [`docs/api-contract.md`](docs/api-contract.md)                   | Full API spec                                |
| [`docs/data-layer.md`](docs/data-layer.md)                       | `@dar/data` design (SWR + debounce)          |
| [`docs/agents/pr-workflow.md`](docs/agents/pr-workflow.md)       | How agents send / review / merge PRs         |
| [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md) | What's auto-mergeable vs human-only        |
| [`docs/agents/decisions.md`](docs/agents/decisions.md)           | Decisions log                                |
| [`scripts/README.md`](scripts/README.md)                         | `lint.sh` / `build.sh` / `deploy.sh`         |
| [`examples/README.md`](examples/README.md)                       | Demo Django apps                             |

---

## Developer scripts

```bash
./scripts/lint.sh        # ruff + black + isort + flake8 + pylint + mypy + bandit + prettier + tsc
./scripts/build.sh       # pnpm install + vite build + poetry build (wheel ships pre-built SPA)
./scripts/deploy.sh      # poetry publish to PyPI (requires POETRY_PYPI_TOKEN_PYPI)
```

The Merger runs `./scripts/lint.sh` before every merge — there is
no CI in this repo by design.

---

## License

MIT — see [`LICENSE`](LICENSE).

## Security

Please report security issues privately. See
[`SECURITY.md`](SECURITY.md) §4. Do **not** open a public issue.

## Contributing

Humans and AI agents both welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md). AI agents must also read
[`CLAUDE.md`](CLAUDE.md), [`docs/agents/pr-workflow.md`](docs/agents/pr-workflow.md),
and [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md).
