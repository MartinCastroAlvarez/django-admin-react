# examples/project — the demo Django project

This directory is the shared Django project that hosts every
`examples/*` app and the `django_admin_react` package under
development. It exists so contributors and reviewers can run the React
admin end-to-end with realistic data.

## What's here

- `settings.py` — minimal, dev-safe settings. SQLite, dev-only
  `SECRET_KEY` if `DJANGO_SECRET_KEY` is unset, both example apps and
  `django_admin_react` in `INSTALLED_APPS`.
- `urls.py` — mounts both the legacy HTML admin at `/admin/legacy/`
  and the React admin at `/admin-react/`. Reviewers can compare the
  two side-by-side.
- `manage.py` — adds the repo root to `sys.path` so
  `examples.<app>` imports resolve regardless of where the consumer
  invokes the command.
- `wsgi.py` / `asgi.py` — standard Django entry points.

## What's **not** here

- A populated `db.sqlite3` — the database is generated on first
  `migrate` and is gitignored.
- A `local_settings.py` with secrets — that file is gitignored too.
  Real secrets go in environment variables or your local shell only.
- A `Procfile`, `Dockerfile`, or any production-deploy artifact. This
  is a development demo, not a deployable site.

## Running

```bash
# from the repo root
poetry install
poetry run python examples/project/manage.py migrate
poetry run python examples/project/manage.py createsuperuser
poetry run python examples/project/manage.py runserver
```

Then:

- **Legacy admin (control group)**: http://localhost:8000/admin/legacy/
- **React admin**: http://localhost:8000/admin-react/ — works once
  PR #5 (write endpoints) lands. Before that, the React mount serves
  a placeholder.

## Why both admins are mounted

Mounting both side-by-side is the safest way to dog-food the React
admin while it's pre-1.0. The reviewer can:

- Edit a model in `/admin/legacy/`.
- Refresh `/admin-react/`.
- See the change immediately — proving the two UIs read from the same
  `ModelAdmin` definitions.

Once the React admin reaches feature parity (post-v1), the legacy
mount can be removed by deleting one line in `urls.py`.

## Security notes

- `SECRET_KEY` is dev-only (auto-generated if `DJANGO_SECRET_KEY` is
  unset). **Never commit a real secret here.** See
  [`../../SECURITY.md`](../../SECURITY.md) §5.
- `DEBUG=True` by default — turn it off with `DJANGO_DEBUG=0` before
  exposing the project on any non-`localhost` interface.
- Even in dev, CSRF and session cookies are enforced. We never
  disable them.

## Adding a new example app

1. Create `examples/<your-app>/` with the usual Django app layout
   (`apps.py`, `models.py`, `admin.py`, `migrations/__init__.py`,
   `tests/`, `README.md`).
2. Add `"examples.<your-app>"` to `INSTALLED_APPS` in `settings.py`.
3. Open a PR. Follow [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md).
