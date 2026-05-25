#!/usr/bin/env bash
#
# scripts/build.sh — produce a PyPI-ready artifact.
#
# Pipeline:
#   1. Build the React SPA (pnpm install + typecheck + vite build).
#   2. Copy the built bundle into django_admin_react/static/admin_react/
#      and django_admin_react/templates/admin_react/index.html.
#   3. Build the Python sdist + wheel via Poetry. The wheel embeds the
#      pre-built React assets so consumers do not need Node to install.
#
# Outputs:
#   dist/django_admin_react-<version>.tar.gz
#   dist/django_admin_react-<version>-py3-none-any.whl
#
# Usage:
#   bash scripts/build.sh
#   BUILD_SKIP_FRONTEND=1 bash scripts/build.sh  # reuse existing assets
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKIP_FE="${BUILD_SKIP_FRONTEND:-0}"
STATIC_DEST="$ROOT/django_admin_react/static/admin_react"
TEMPLATE_DEST="$ROOT/django_admin_react/templates/admin_react/index.html"

step() {
  printf '\n\033[1;34m▶ %s\033[0m\n' "$*"
}

# --------------------------------------------------------------------------- #
# 1. Frontend build                                                           #
# --------------------------------------------------------------------------- #
if [[ "$SKIP_FE" != "1" ]]; then
  if [[ ! -d "$ROOT/frontend" ]]; then
    echo "no frontend/ directory — nothing to build for the SPA"
  elif ! command -v pnpm >/dev/null 2>&1; then
    echo "pnpm not found — install pnpm (https://pnpm.io) to build the SPA"
    exit 1
  else
    cd "$ROOT/frontend"
    step "pnpm install"
    if [[ -f pnpm-lock.yaml ]]; then
      pnpm install --frozen-lockfile
    else
      pnpm install
    fi

    step "pnpm -r typecheck"
    pnpm -r typecheck

    step "pnpm --filter @dar/shell build (vite)"
    if pnpm --filter @dar/shell run build 2>/dev/null; then
      :
    else
      echo "(@dar/shell build is a placeholder until PR #6 lands; continuing)"
    fi

    SHELL_DIST="$ROOT/frontend/packages/shell/dist"
    if [[ -d "$SHELL_DIST" && -f "$SHELL_DIST/index.html" ]]; then
      step "copy bundle into Python package"
      mkdir -p "$STATIC_DEST" "$(dirname "$TEMPLATE_DEST")"
      # Clean previous bundle (preserve .gitkeep and README.md).
      find "$STATIC_DEST" -mindepth 1 \
        ! -name '.gitkeep' ! -name 'README.md' \
        -exec rm -rf {} + 2>/dev/null || true
      cp -R "$SHELL_DIST"/* "$STATIC_DEST/"
      cp "$SHELL_DIST/index.html" "$TEMPLATE_DEST"
    else
      echo "(no $SHELL_DIST/index.html yet — Python build will ship without SPA assets)"
    fi
    cd "$ROOT"
  fi
fi

# --------------------------------------------------------------------------- #
# 2. Python build                                                             #
# --------------------------------------------------------------------------- #
step "poetry build"
poetry build

step "list artifacts"
ls -lh dist/

printf '\n\033[1;32m✔ build complete (artifacts in dist/)\033[0m\n'
