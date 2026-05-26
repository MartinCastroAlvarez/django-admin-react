#!/usr/bin/env bash
#
# scripts/screenshots.sh — capture docs/screenshots/*.png from the
# running example project via Playwright.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${DAR_PORT:-8765}"
BASE_URL="http://127.0.0.1:${PORT}"

DB="$ROOT/.dar-screenshots.sqlite3"
MANAGE="examples/project/manage.py"

USER="screenshots"
PASS="screenshots-only-do-not-reuse"

step() { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }

step "fresh sqlite ${DB}"
rm -f "$DB"

step "makemigrations + migrate"
poetry run python "$MANAGE" makemigrations --no-input >/dev/null
poetry run python "$MANAGE" migrate --no-input >/dev/null

step "create one-off screenshot superuser"
poetry run python "$MANAGE" shell <<EOF
from django.contrib.auth import get_user_model
U = get_user_model()
U.objects.filter(username="${USER}").delete()
U.objects.create_superuser(username="${USER}", email="${USER}@example.invalid", password="${PASS}")
EOF

step "seed deterministic fixture data"
poetry run python "$MANAGE" shell <<'EOF'
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
User = get_user_model()
demo_user, _ = User.objects.get_or_create(
    username="alice",
    defaults={"is_staff": False, "is_active": True, "email": "alice@example.invalid"},
)
try:
    from examples.library.models import Author, Book, Genre
    for n in ("Fiction", "Science", "History"):
        Genre.objects.get_or_create(name=n)
    authors_data = [
        ("Ada L.", "United Kingdom", date(1815, 12, 10)),
        ("Grace H.", "United States", date(1906, 12, 9)),
        ("Donald K.", "United States", date(1938, 1, 10)),
        ("Barbara L.", "United States", date(1939, 8, 21)),
        ("Margaret H.", "United States", date(1936, 6, 9)),
    ]
    for name, country, born in authors_data:
        Author.objects.get_or_create(name=name, defaults={"country": country, "born": born})
    auths = list(Author.objects.all().order_by("name")[:3])
    Book.objects.get_or_create(isbn="978-0000000001", defaults={"title": "Notes on the Analytical Engine", "author": auths[0], "language": "en"})
    Book.objects.get_or_create(isbn="978-0000000002", defaults={"title": "On Compilers and Cobol", "author": auths[1], "language": "en"})
    Book.objects.get_or_create(isbn="978-0000000003", defaults={"title": "The Art of Programming", "author": auths[2], "language": "en"})
except Exception as e:
    print("library seed skipped:", e)
EOF

step "boot runserver on :${PORT}"
poetry run python "$MANAGE" runserver "127.0.0.1:${PORT}" --noreload --insecure \
  >/tmp/dar-rs.log 2>&1 &
SERVER_PID=$!
trap 'kill ${SERVER_PID} 2>/dev/null || true; wait ${SERVER_PID} 2>/dev/null || true' EXIT

for i in $(seq 1 40); do
  if curl -fsS "${BASE_URL}/admin/legacy/login/" >/dev/null 2>&1; then break; fi
  sleep 0.25
done

step "playwright capture"
PW_DIR="/tmp/dar-pw"
if [[ ! -d "$PW_DIR/node_modules/playwright" ]]; then
  step "install playwright to ${PW_DIR}"
  mkdir -p "$PW_DIR" && (cd "$PW_DIR" && npm init -y >/dev/null && npm install playwright@1.60.0 --no-package-lock >/dev/null)
fi
ln -sfn "${PW_DIR}/node_modules" "$ROOT/scripts/node_modules"
DAR_BASE_URL="${BASE_URL}" DAR_USER="${USER}" DAR_PASS="${PASS}" \
  node scripts/screenshots.mjs

step "done"
ls -lh docs/screenshots/*.png 2>/dev/null || true
