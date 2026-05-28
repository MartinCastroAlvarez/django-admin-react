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
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from django.contrib.auth import get_user_model
User = get_user_model()
demo_user, _ = User.objects.get_or_create(
    username="alice",
    defaults={"is_staff": False, "is_active": True, "email": "alice@example.invalid"},
)
# library — small literature catalogue.
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

# fintech — richer admin (list_filter, date_hierarchy, autocomplete,
# readonly, admin.display) for the screenshot captures.
try:
    from examples.fintech.models import Account, Transaction, Card
    owner, _ = User.objects.get_or_create(
        username="screenshots-owner",
        defaults={"email": "owner@example.invalid", "is_active": True},
    )
    accounts_data = [
        ("Operating cash",    "USD", Decimal("128450.10"), True,  "DE89370400440532013010"),
        ("Payroll",           "USD", Decimal("42010.00"),  True,  "DE89370400440532013020"),
        ("Treasury reserve",  "EUR", Decimal("960000.00"), True,  "DE89370400440532013030"),
        ("Petty cash",        "USD", Decimal("310.50"),    True,  "DE89370400440532013040"),
        ("Closed (Legacy)",   "USD", Decimal("0.00"),      False, "DE89370400440532013050"),
    ]
    for name, currency, balance, is_active, iban in accounts_data:
        Account.objects.get_or_create(
            name=name,
            defaults={
                "owner": owner,
                "currency": currency,
                "balance": balance,
                "is_active": is_active,
                "iban": iban,
            },
        )
    accounts = list(Account.objects.all().order_by("name"))
    tx_data = [
        (0, "credit", Decimal("12500.00"),  "Customer invoice #1024",  3),
        (0, "debit",  Decimal("4200.00"),   "AWS — monthly compute",   6),
        (0, "credit", Decimal("8950.50"),   "Customer invoice #1025",  9),
        (3, "debit",  Decimal("32000.00"),  "Bi-weekly payroll",      14),
        (3, "credit", Decimal("32000.00"),  "Funding from operating", 14),
        (4, "credit", Decimal("250000.00"), "Treasury sweep",         21),
        (4, "debit",  Decimal("12500.00"),  "Bond coupon payment",    28),
        (2, "debit",  Decimal("45.20"),     "Office supplies",         2),
        (2, "debit",  Decimal("12.10"),     "Coffee — team meeting",   1),
    ]
    base = datetime.now(timezone.utc)
    for i, (idx, kind, amount, description, days_ago) in enumerate(tx_data):
        Transaction.objects.get_or_create(
            reference=f"TXN-2026-{i+101:04d}",
            defaults={
                "account": accounts[idx % len(accounts)],
                "kind": kind,
                "amount": amount,
                "description": description,
                "posted_at": base - timedelta(days=days_ago, hours=i),
            },
        )
    cards_data = [
        ("Alice Operations",  0, "4242", "active"),
        ("Bob Treasury",      4, "9001", "active"),
        ("Carol — Office",    2, "1122", "blocked"),
    ]
    for holder, idx, last4, status in cards_data:
        Card.objects.get_or_create(
            last4=last4,
            defaults={
                "holder_name": holder,
                "account": accounts[idx % len(accounts)],
                "expires_at": date(2030, 12, 1),
                "status": status,
            },
        )
except Exception as e:
    print("fintech seed skipped:", e)
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
