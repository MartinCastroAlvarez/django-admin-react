# examples/fintech — Fintech demo app

A small consumer-facing Django app that demonstrates how
`django-admin-react` surfaces a realistic Fintech model graph through the
React UI.

## What's here

- `models.py` — `Account`, `Transaction`, `Statement`, `Card`.
- `admin.py` — `ModelAdmin` subclasses exercising the contract this
  package depends on:
  - `list_display`, `list_filter`, `search_fields`
  - `readonly_fields` (e.g., `iban`, `created_at`, `last4`)
  - `autocomplete_fields` (FK pickers — currently rendered as a basic
    FK input in the React UI; full autocomplete is post-v1)
  - `has_delete_permission` override on `AccountAdmin` (only superusers
    can delete accounts) — the React UI hides the delete button for
    non-superusers automatically.
  - A `@admin.display`-decorated callable (`Card.masked_number`) to
    confirm callable `list_display` values render correctly.
- `migrations/` — empty until `makemigrations` is run by the consumer
  project.
- `tests/test_admin.py` — smoke test: all models are registered.

## What's **not** here

- A `settings.py` — this is a Django app, not a project. It is
  installed by `examples/project/` (the shared demo project) and gets
  its database from there.
- Sample data fixtures with PII or anything that looks like real
  customer data. Fixtures, if any, are added later in
  `examples/project/fixtures/` and only contain obviously-synthetic
  values.
- Any reference to `django_admin_react` — this app is intentionally
  agnostic. It works with the stock admin **and** with this package.

## Why this app demonstrates the design

- **Sensitive data**: `Card.last4` shows how we expose only the last 4
  digits — the React UI receives `last4` (a non-sensitive prefix
  designed for display), never a full PAN. There is no full-PAN field
  in the model; that's intentional: don't store what you don't need.
- **Permission gating**: `AccountAdmin.has_delete_permission` returns
  `False` for non-superusers, so the React UI hides the delete button
  automatically. No React code change required.
- **Readonly fields**: `iban`, `created_at`, `last4` are read-only in
  the admin form, so the API rejects writes to them and the UI renders
  them as static text.
- **Foreign keys**: `Transaction → Account → User` exercises the
  `{"id": ..., "label": ...}` FK serialization contract from
  [`docs/api-contract.md`](../../docs/api-contract.md) §4.

## Running

When `examples/project/` is wired up (PR #8), you'll be able to:

```bash
cd examples/project
poetry run python manage.py migrate
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
# Visit http://localhost:8000/admin-react/
```

Until then, this app boots inside the package's test project. Smoke
tests run with:

```bash
poetry run pytest examples/fintech/tests/
```
