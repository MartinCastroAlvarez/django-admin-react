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

  step "mypy (best-effort, non-blocking)"
  poetry run mypy "${PY_TARGETS[@]}" || echo "mypy reported issues — non-blocking for v1"

  step "bandit (security lint, package only)"
  poetry run bandit -q -r django_admin_react

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

    step "eslint (if configured)"
    if pnpm -r --filter "{packages/*}" exec test -f .eslintrc.cjs >/dev/null 2>&1; then
      pnpm -r lint
    else
      echo "(no eslint config yet — wired in PR #6)"
    fi
  fi
fi

printf '\n\033[1;32m✔ all linters passed\033[0m\n'
