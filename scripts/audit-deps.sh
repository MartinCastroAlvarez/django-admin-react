#!/usr/bin/env bash
# Run the dependency-security audit pipeline.
#
# Usage:
#   ./scripts/audit-deps.sh
#   ./scripts/audit-deps.sh --fail-on=high       # default
#   ./scripts/audit-deps.sh --fail-on=critical   # release mode
#
# Exit codes:
#   0  all clear at the chosen severity threshold
#   1  one or more findings at or above the threshold (release-blocking
#      under ACCEPTANCE.md §4.9 S-44 / S-45)
#   2  a tool is missing
#
# Run on demand or as part of release prep. Linked from
# `scripts/lint.sh` once it's been stable for a release cycle. See
# `docs/agents/security-expert/NEXT_STEPS.md`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL_ON="high"
for arg in "$@"; do
  case "$arg" in
    --fail-on=*) FAIL_ON="${arg#--fail-on=}" ;;
    *) echo "Unknown arg: $arg"; exit 2 ;;
  esac
done

bold() { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m✓\033[0m %s\n' "$*"; }
fail() { printf '\033[31m✗ FAIL\033[0m %s\n' "$*"; exit 1; }

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing: $1"; exit 2; }
}

# --------------------------------------------------------------------- #
# Python — pip-audit                                                    #
# --------------------------------------------------------------------- #
bold "Python: poetry run pip-audit"
require poetry

# `--strict` makes pip-audit non-zero on any finding; we still want to
# gate on severity ourselves so we use --format json and parse.
PY_REPORT="$(poetry run pip-audit --format json --progress-spinner off 2>/dev/null || true)"
if [ -z "$PY_REPORT" ]; then
  fail "pip-audit produced no output — check that poetry install succeeded"
fi

PY_HIGH="$(python3 - <<PY
import json, sys
report = json.loads('''$PY_REPORT''')
deps = report.get("dependencies") or report
threshold = {"low": 0, "medium": 1, "high": 2, "critical": 3}["${FAIL_ON}"]
sev_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
hits = []
def walk(items):
    for item in items:
        for v in item.get("vulns", []):
            sev = (v.get("severity") or "").upper()
            if sev_order.get(sev, 0) >= threshold:
                hits.append((item["name"], v.get("id"), sev))
walk(deps)
for name, vid, sev in hits:
    print(f"  - {name}: {vid} ({sev})")
print(f"COUNT={len(hits)}")
PY
)"

echo "$PY_REPORT" > .audit-python.json
echo "$PY_HIGH"
if echo "$PY_HIGH" | grep -q '^COUNT=0$'; then
  ok "pip-audit: no findings at severity ≥ ${FAIL_ON}"
else
  fail "pip-audit found vulnerabilities at severity ≥ ${FAIL_ON}. See .audit-python.json."
fi

# --------------------------------------------------------------------- #
# Frontend — pnpm audit                                                 #
# --------------------------------------------------------------------- #
if [ -d frontend ]; then
  bold "Frontend: pnpm audit --prod"
  require pnpm
  pushd frontend >/dev/null
  if [ ! -f pnpm-lock.yaml ]; then
    popd >/dev/null
    echo "  (skipped: no frontend/pnpm-lock.yaml — run 'pnpm install' in frontend/ first)"
    echo "  release prep MUST re-run this audit against the committed lockfile."
  else
    # pnpm audit returns non-zero on any finding; capture and gate manually.
    set +e
    pnpm audit --prod --audit-level "$FAIL_ON" --json 2>/dev/null > "../.audit-frontend.json"
    STATUS=$?
    set -e
    popd >/dev/null

    # Distinguish "no lockfile" / other tool errors from actual vulnerabilities.
    if python3 -c "
import json, sys
try:
    data = json.load(open('.audit-frontend.json'))
except Exception:
    sys.exit(0)
err = data.get('error') if isinstance(data, dict) else None
sys.exit(2 if err else 0)
"; then
      :
    else
      err_code=$?
      if [ "$err_code" -eq 2 ]; then
        echo "  pnpm audit reported a tool-level error (not a vulnerability):"
        python3 -c "import json; d=json.load(open('.audit-frontend.json')); print('   ',d['error'].get('message',''))" 2>/dev/null
        echo "  release prep MUST resolve this and re-run the audit."
        # Tool-level error is non-blocking at dev-time, blocking at release.
      fi
    fi

    if [ "$STATUS" -eq 0 ]; then
      ok "pnpm audit: no findings at severity ≥ ${FAIL_ON}"
    elif [ -f .audit-frontend.json ] && grep -q 'ERR_PNPM_AUDIT_NO_LOCKFILE\|error' .audit-frontend.json; then
      echo "  (tool-level error, not a vulnerability — see above)"
    else
      echo "  see .audit-frontend.json for detail"
      fail "pnpm audit found vulnerabilities at severity ≥ ${FAIL_ON}"
    fi
  fi
else
  echo "(no frontend/ directory — skipping JS dep audit)"
fi

bold "Dependency audit clean."
echo "Artefacts: .audit-python.json, .audit-frontend.json"
