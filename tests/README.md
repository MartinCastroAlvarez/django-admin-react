# tests/ — Python test suite

Pytest-driven tests for the Django package. Frontend tests live under
`frontend/packages/<pkg>/tests/`.

## Layout

```
tests/
├── conftest.py             # Shared fixtures (Django setup, users, factories)
├── test_project/           # Minimal Django project used by tests
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── testapp/
│       ├── __init__.py
│       ├── apps.py
│       ├── admin.py
│       ├── models.py       # Synthetic models exercising every field type
│       └── migrations/
├── api/                    # Tests grouped by endpoint
│   ├── test_registry.py
│   ├── test_list.py
│   ├── test_detail.py
│   ├── test_create.py
│   ├── test_update.py
│   └── test_delete.py
├── test_conf.py
├── test_serializers.py
└── test_permissions.py
```

## Required matrix per endpoint

See [`SECURITY.md`](../SECURITY.md) §3 and [`CLAUDE.md`](../CLAUDE.md) §6.
Minimum cases for each endpoint:

- Anonymous → rejected.
- Authenticated non-staff → 403.
- Staff with permission → success.
- Staff without per-model `has_*_permission` → 403.
- Unregistered model → 404.
- Non-existent pk → 404.
- Write to readonly/excluded field → 400.
- CSRF missing on unsafe method → 403.
- Returned `permissions` booleans match `ModelAdmin.has_*_permission`.
- Sensitive-shaped fields (`password`, `token`, `api_key`, ...) never
  appear in any response.

## Running

```bash
poetry install
poetry run pytest                          # all tests
poetry run pytest tests/api/test_list.py   # one file
poetry run pytest -k "not slow"            # exclude slow tests
poetry run pytest --cov=django_admin_react # coverage report
```

## Status

Test scaffolding (this README + folder layout) lands in PR #1.
`tests/test_project/` and the per-endpoint test files land alongside
the endpoints they cover (PRs #3-#5). Frontend tests land in PR #6 / #7.

## Rules

- No real network. No real database (use SQLite in-memory).
- Synthetic data only. No real names, emails, accounts.
- Never `xfail`/`skip` a security test to make CI green. File an issue.
