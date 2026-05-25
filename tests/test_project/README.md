# tests/test_project/

A minimal Django project used only by the pytest suite.

- `settings.py` — in-memory SQLite, the bare middleware needed for
  session + CSRF + admin, and `django_admin_react` in
  `INSTALLED_APPS`.
- `urls.py` — mounts `django.contrib.admin` at `/admin/` and
  `django_admin_react` at `/admin-react/` so tests exercise the
  configurable mount point.

## What does **not** belong here

- Production-shaped settings. This is a test fixture, not a template
  for consumers — consumers should follow `docs/installation.md`
  instead.
- Sensitive defaults. The `SECRET_KEY` is generated per-run with
  `secrets.token_urlsafe`; nothing here should ever be reused outside
  of tests.
- Test cases. Those live one level up in `tests/test_*.py`.
