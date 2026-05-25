# django_admin_react/static/admin_react/

The built React bundle drops here at packaging time. Nothing checked
in to git except this README and `.gitkeep`.

The build step (run from `frontend/`):

```bash
pnpm --filter @dar/shell build
poetry run dar-build-frontend  # (script lands in PR #6)
```

copies the hashed JS, CSS, and any static assets here so the wheel
shipped to PyPI contains a ready-to-serve bundle. Consumers do not
need Node to install the package.
