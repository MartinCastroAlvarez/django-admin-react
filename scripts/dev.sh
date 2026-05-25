#!/usr/bin/env bash
#
# scripts/dev.sh — boot the example Django project for local development.
#
# Usage (via pnpm):
#   pnpm run dev                # all example apps installed; visit any
#   pnpm run dev:fintech        # banner focuses on /admin-react/fintech/
#   pnpm run dev:library        # banner focuses on /admin-react/library/
#   pnpm run dev:blog           # banner focuses on /admin-react/blog/
#   pnpm run dev:ecommerce      # banner focuses on /admin-react/ecommerce/
#   pnpm run dev:hr             # banner focuses on /admin-react/hr/
#
# The dev server runs `examples/project/manage.py runserver`. Every
# example app is installed in `examples/project/settings.py`, so any
# of them is reachable from a single `runserver`. The `EXAMPLE_APP`
# env var only controls the welcome banner.
#
# Pre-conditions (validated, will exit cleanly if missing):
#   - poetry available and `poetry install` has been run.
#   - sqlite3 (default db) is writable in the project dir.
#
# Side effects on first run:
#   - Migrations applied (`manage.py migrate --no-input`).
#   - A superuser is auto-created if none exists, using the env vars
#     DJANGO_DEV_SUPERUSER / DJANGO_DEV_SUPERUSER_PASSWORD (defaults
#     to admin / admin — DEV ONLY). The script refuses to set these
#     defaults if DJANGO_DEBUG is "0".
#
# Exit codes:
#   0 — server started (then runs until Ctrl-C).
#   1 — poetry not found.
#   2 — DJANGO_DEBUG=0 while using default credentials.
#   3 — other pre-condition failure.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$ROOT/examples/project"
HOST="${DJANGO_DEV_HOST:-127.0.0.1}"
PORT="${DJANGO_DEV_PORT:-8000}"
APP="${EXAMPLE_APP:-}"

step() {
  printf '\n\033[1;34m▶ %s\033[0m\n' "$*"
}

if ! command -v poetry >/dev/null 2>&1; then
  echo "poetry not found on PATH. Install Poetry first." >&2
  exit 1
fi

if [[ ! -d "$PROJECT" ]]; then
  echo "expected $PROJECT — example project not in repo." >&2
  exit 3
fi

cd "$ROOT"

step "poetry install (idempotent)"
poetry install --quiet --no-interaction

step "migrate"
poetry run python "$PROJECT/manage.py" migrate --no-input

# Auto-superuser, dev-only.
if [[ "${DJANGO_DEBUG:-1}" != "0" ]]; then
  ADMIN_USER="${DJANGO_DEV_SUPERUSER:-admin}"
  ADMIN_PASS="${DJANGO_DEV_SUPERUSER_PASSWORD:-admin}"
  step "ensure dev superuser '$ADMIN_USER' (DEV ONLY; DJANGO_DEBUG!=0)"
  poetry run python "$PROJECT/manage.py" shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$ADMIN_USER').exists():
    User.objects.create_superuser('$ADMIN_USER', 'admin@example.com', '$ADMIN_PASS')
    print('created superuser: $ADMIN_USER / $ADMIN_PASS')
else:
    print('superuser exists: $ADMIN_USER')
"
elif [[ -n "${DJANGO_DEV_SUPERUSER:-}" ]]; then
  echo "DJANGO_DEBUG=0 with DJANGO_DEV_SUPERUSER set — refusing to" >&2
  echo "auto-create a credential in non-dev mode. Use createsuperuser." >&2
  exit 2
fi

# Welcome banner.
echo
echo "  ════════════════════════════════════════════════════════════════"
echo "   django-admin-react — local dev"
echo "  ────────────────────────────────────────────────────────────────"
echo "   legacy admin:  http://$HOST:$PORT/admin/legacy/"
echo "   React admin:   http://$HOST:$PORT/admin-react/"
if [[ -n "$APP" ]]; then
  echo "   focus app:     $APP"
  case "$APP" in
    fintech)   echo "                  models: Account, Transaction, Statement, Card" ;;
    library)   echo "                  models: Genre, Author, Book, Member, Loan" ;;
    blog)      echo "                  models: Category, Tag, Post, Comment" ;;
    ecommerce) echo "                  models: Category, Product, Customer, Order, OrderItem" ;;
    hr)        echo "                  models: Department, Role, Employee, TimeOff, PerformanceReview" ;;
    *)         echo "                  (unknown app — no model hint)" ;;
  esac
fi
echo "   login:         ${DJANGO_DEV_SUPERUSER:-admin} / ${DJANGO_DEV_SUPERUSER_PASSWORD:-admin}"
echo "                  (DEV ONLY — never use these creds anywhere else)"
echo "  ════════════════════════════════════════════════════════════════"
echo

step "runserver"
exec poetry run python "$PROJECT/manage.py" runserver "$HOST:$PORT"
