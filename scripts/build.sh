#!/usr/bin/env bash
#
# scripts/build.sh — produce a PyPI-ready artifact.
#
# Pipeline:
#   1. Build the React SPA via Vite (pnpm install + typecheck +
#      pnpm --filter @dar/web run build). Vite writes the bundle and
#      manifest directly into django_admin_react/static/admin_react/
#      — no copy step needed (see frontend/apps/web/vite.config.ts).
#   2. Verify the manifest landed where SpaIndexView expects it.
#   3. Build the Python sdist + wheel via Poetry. The wheel embeds
#      the pre-built React assets so consumers do not need Node.
#
# Outputs:
#   dist/django_admin_react-<version>.tar.gz
#   dist/django_admin_react-<version>-py3-none-any.whl
#
# Usage:
#   bash scripts/build.sh
#   BUILD_SKIP_FRONTEND=1 bash scripts/build.sh  # reuse existing bundle
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_FE="${BUILD_SKIP_FRONTEND:-0}"
STATIC_DEST="$ROOT/django_admin_react/static/admin_react"
MANIFEST="$STATIC_DEST/.vite/manifest.json"

step() {
  printf '\n\033[1;34m▶ %s\033[0m\n' "$*"
}

# --------------------------------------------------------------------------- #
# 1. Frontend build (Vite writes directly into the Python package's static/)  #
# --------------------------------------------------------------------------- #
if [[ "$SKIP_FE" != "1" ]]; then
  if [[ ! -d "$ROOT/frontend" ]]; then
    echo "no frontend/ directory — nothing to build for the SPA" >&2
    exit 3
  fi
  if ! command -v pnpm >/dev/null 2>&1; then
    echo "pnpm not found — install pnpm (https://pnpm.io) to build the SPA" >&2
    exit 1
  fi

  cd "$ROOT/frontend"

  step "pnpm install"
  if [[ -f pnpm-lock.yaml ]]; then
    pnpm install --frozen-lockfile
  else
    pnpm install
  fi

  step "pnpm -r typecheck"
  pnpm -r typecheck

  step "pnpm --filter @dar/web run build (vite)"
  pnpm --filter @dar/web run build

  cd "$ROOT"
fi

# --------------------------------------------------------------------------- #
# 2. Sanity check                                                             #
# --------------------------------------------------------------------------- #
if [[ ! -f "$MANIFEST" ]]; then
  echo "expected Vite manifest at $MANIFEST but it is missing — Python build aborted" >&2
  echo "(re-run without BUILD_SKIP_FRONTEND, or run 'pnpm run build:vite' manually)" >&2
  exit 2
fi

# --------------------------------------------------------------------------- #
# 3. Python build                                                             #
# --------------------------------------------------------------------------- #
step "poetry build"
poetry build

step "list artifacts"
ls -lh dist/

printf '\n\033[1;32m✔ build complete (artifacts in dist/)\033[0m\n'
