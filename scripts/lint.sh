#!/usr/bin/env bash
#
# scripts/lint.sh — run every Python and frontend linter the project
# requires before merge. Exits non-zero on the first failure.
#
# Usage:
#   bash scripts/lint.sh             # full sweep
#   LINT_PY_ONLY=1 bash scripts/lint.sh   # skip frontend
#   LINT_FE_ONLY=1 bash scripts/lint.sh   # skip Python
#
# The project does not run CI for now (per repo-owner direction); every
# contributor must run this locally before opening / merging a PR.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY_ONLY="${LINT_PY_ONLY:-0}"
FE_ONLY="${LINT_FE_ONLY:-0}"

step() {
  printf '\n\033[1;34m▶ %s\033[0m\n' "$*"
}

# --------------------------------------------------------------------------- #
# pre-commit (secret + security hooks)                                        #
# --------------------------------------------------------------------------- #
# `.pre-commit-config.yaml` carries gitleaks + bandit + the custom
# pygrep security hooks (no-objects-all-in-api, no-csrf-exempt,
# no-user-has-perm, no-dar-api-from-pages, no-partial-tokens). A fresh
# checkout has them INACTIVE until a contributor runs `pre-commit
# install`, so run them here as part of the lint sweep too — that way
# the security patterns are enforced even on a checkout where the git
# hook was never installed. Graceful skip with a loud hint when the
# `pre-commit` binary is absent rather than a hard failure (#144).
if command -v pre-commit >/dev/null 2>&1; then
  step "pre-commit run --all-files (gitleaks + bandit + security pygrep)"
  pre-commit run --all-files
else
  step "pre-commit (SKIPPED — binary not found)"
  echo "  ⚠ pre-commit is not installed; the gitleaks + security hooks did NOT run."
  echo "    Install it:  pipx install pre-commit  (then: pre-commit install)"
  echo "    Until then, the secret-scan + security pygrep gates are unenforced locally."
fi

# --------------------------------------------------------------------------- #
# Python                                                                      #
# --------------------------------------------------------------------------- #
if [[ "$FE_ONLY" != "1" ]]; then
  PY_TARGETS=(django_admin_react tests)

  step "ruff check"
  poetry run ruff check "${PY_TARGETS[@]}"

  step "ruff format --check"
  poetry run ruff format --check "${PY_TARGETS[@]}"

  step "black --check"
  poetry run black --check "${PY_TARGETS[@]}"

  step "isort --check-only"
  poetry run isort --check-only "${PY_TARGETS[@]}"

  step "flake8"
  poetry run flake8 "${PY_TARGETS[@]}"

  step "pylint (errors only)"
  poetry run pylint --errors-only "${PY_TARGETS[@]}"

  # The package must stay mypy-clean (it regressed silently once — #312 —
  # precisely because mypy was non-blocking here). Tests carry known
  # annotation gaps (#318), so they stay best-effort for now.
  step "mypy (package — BLOCKING; must stay clean)"
  poetry run mypy django_admin_react

  step "mypy (tests — best-effort; gaps tracked in #318)"
  poetry run mypy tests || echo "mypy on tests reported issues — non-blocking (see #318)"

  step "bandit (security lint, package only — config in pyproject [tool.bandit])"
  poetry run bandit -c pyproject.toml -q -r django_admin_react

  step "pytest"
  poetry run pytest -q
fi

# --------------------------------------------------------------------------- #
# Frontend                                                                    #
# --------------------------------------------------------------------------- #
if [[ "$PY_ONLY" != "1" ]]; then
  if [[ ! -d "$ROOT/frontend" ]]; then
    echo "(no frontend/ directory — skipping frontend linters)"
  elif ! command -v pnpm >/dev/null 2>&1; then
    echo "pnpm not found — install pnpm (https://pnpm.io) to run frontend linters"
    exit 1
  else
    cd "$ROOT/frontend"

    step "pnpm install (frozen lockfile if present)"
    if [[ -f pnpm-lock.yaml ]]; then
      pnpm install --frozen-lockfile
    else
      pnpm install
    fi

    step "prettier --check"
    pnpm exec prettier --check "packages/**/*.{ts,tsx,js,jsx,json,md}" || true

    step "tsc --noEmit (typecheck across workspace)"
    pnpm -r typecheck

    step "eslint + stylelint (pnpm lint — root flat config, eslint --max-warnings 0)"
    # `frontend/eslint.config.mjs` (flat config) + `.stylelintrc.json`
    # are at the workspace root, not per-package, so probing each package
    # for a legacy `.eslintrc.cjs` (the old behaviour) silently skipped
    # the whole gate. Invoke the package.json `lint` script directly so
    # the Merger's sweep actually runs the eslint + stylelint gate (#261).
    pnpm lint
  fi
fi

printf '\n\033[1;32m✔ all linters passed\033[0m\n'
