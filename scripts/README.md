# scripts/

Local automation. Three entry points cover the developer workflow:

| Script             | Purpose                                                                                             |
| ------------------ | --------------------------------------------------------------------------------------------------- |
| `scripts/lint.sh`  | Run every Python + frontend linter and test. Must pass before merging a PR.                         |
| `scripts/build.sh` | Build the React SPA, copy the bundle into the Python package, and produce a PyPI-ready sdist+wheel. |
| `scripts/deploy.sh`| Upload the built artifact to PyPI (or TestPyPI with `--test`). Token-gated.                         |

All scripts are POSIX `bash`, use `set -euo pipefail`, and are safe to
re-run.

## Why scripts and not CI

The repo owner has deferred CI/CD for now. Every contributor (human or
agent) runs `scripts/lint.sh` locally before opening or merging a PR.
This file and `CONTRIBUTING.md` document the workflow.

## What gets run by `lint.sh`

Python:

- `ruff check` and `ruff format --check`
- `black --check`
- `isort --check-only` (configured for `force_single_line` per repo
  policy — one import per line)
- `flake8`
- `pylint --errors-only`
- `mypy` (best-effort; non-blocking)
- `bandit` (security lint on the package)
- `pytest`

Frontend (when `frontend/` exists and `pnpm` is installed):

- `pnpm install --frozen-lockfile`
- `prettier --check`
- `tsc --noEmit` (typecheck workspace-wide)
- `pnpm -r lint` (eslint, once wired in PR #6)

Use `LINT_PY_ONLY=1` to skip frontend, `LINT_FE_ONLY=1` to skip Python.

## Build pipeline (`build.sh`)

1. `pnpm install --frozen-lockfile && pnpm -r typecheck && pnpm --filter @dar/shell build`
2. Copy `frontend/packages/shell/dist/` into
   `django_admin_react/static/admin_react/` and
   `frontend/packages/shell/dist/index.html` into
   `django_admin_react/templates/admin_react/index.html`.
3. `poetry build` → `dist/*.tar.gz` and `dist/*-py3-none-any.whl` with
   the pre-built SPA bundled inside the wheel.

Consumers installing via `pip install django-admin-react` never need
Node — the wheel ships the built assets.

Use `BUILD_SKIP_FRONTEND=1` to reuse existing `static/admin_react/`
assets (e.g., when iterating on Python code only).

## Deploy (`deploy.sh`)

```bash
PYPI_TOKEN=pypi-…  bash scripts/deploy.sh           # prod PyPI (gated)
TESTPYPI_TOKEN=pypi-…  bash scripts/deploy.sh --test  # TestPyPI
```

- Never paste a token on the command line or in any file.
- The script reads the token from the env var and configures Poetry
  via `poetry config pypi-token.pypi …` (Poetry stores it in
  `~/.config/pypoetry/auth.toml`, not in this repo).
- Prod PyPI publish has a 3-second confirmation pause — abort with
  `Ctrl-C` if you did not mean to release.

The repo owner gates prod PyPI publishes; do not run `deploy.sh` (no
`--test`) without their go-ahead.

## Adding a new script

- Keep one concern per script.
- Use `set -euo pipefail` at the top.
- Refuse to leak secrets through `set -x` or `ps` — pass via env vars
  and stdin, never the command line.
- Add it to this README's table.
