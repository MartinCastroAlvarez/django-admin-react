# django_admin_react/ — the Python package

This directory **is** the artifact published to PyPI. Everything else
in the repository supports it.

## Layout

```
django_admin_react/
├── __init__.py          # __version__ and AppConfig entry point
├── apps.py              # Django AppConfig
├── conf.py              # settings.DJANGO_ADMIN_REACT lazy loader
├── urls.py              # mountable URL patterns (api/v1/ + SPA fallback)
├── views.py             # SPA index view
├── api/
│   ├── __init__.py
│   ├── urls.py          # API URL patterns
│   ├── permissions.py   # IsStaffUser + ModelAdmin gates
│   ├── registry.py      # AdminSite introspection helpers
│   ├── serializers.py   # conservative field serialization
│   └── views/           # one file per endpoint (registry/list/detail/...)
├── templates/admin_react/
│   └── index.html       # SPA shell template
└── static/admin_react/  # built React bundle drops here
```

## Rules

- This package may **not** import from `frontend/`, `examples/`, or
  `tests/`. It is self-contained.
- It may **not** import a consumer's models. All access goes through
  `admin.site._registry` and `ModelAdmin` methods.
- It may **not** hardcode example model names (`Account`, `Book`,
  `Transaction`, …). If you see one, fix it.
- Settings live under a single dict `settings.DJANGO_ADMIN_REACT`. Read
  them through `django_admin_react.conf`, never via
  `django.conf.settings.DJANGO_ADMIN_REACT` directly.

## Implementation status

| File                          | Status             | Lands in PR |
| ----------------------------- | ------------------ | ----------- |
| `__init__.py`, `apps.py`      | Stub               | #1          |
| `conf.py`                     | Stub w/ defaults   | #1 → flesh out in #2 |
| `urls.py`                     | Routes wired, views stubbed | #1 → #6 |
| `views.py`                    | SpaIndexView stub  | #6          |
| `api/permissions.py`          | Empty              | #3          |
| `api/registry.py`             | Empty              | #3          |
| `api/serializers.py`          | Empty              | #4          |
| `api/views/registry.py`       | Empty              | #3          |
| `api/views/list.py`           | Empty              | #4          |
| `api/views/detail.py`         | Empty              | #4          |
| `api/views/create.py`         | Empty              | #5          |
| `api/views/update.py`         | Empty              | #5          |
| `api/views/delete.py`         | Empty              | #5          |
| `templates/admin_react/index.html` | Placeholder  | #6          |
| `static/admin_react/`         | `.gitkeep`         | populated at build time |
