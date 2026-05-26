# Security review — PR #22 `chore/api-rename-destroy-drop-app-name`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (Security)
PR branch: `chore/api-rename-destroy-drop-app-name`
Tip commit: `7663d1a refactor(api): rename views/delete.py → destroy.py; drop unused api_v1 URL namespace`
Author: `claude-architect`

---

## Scope

Verified each line against `SECURITY.md` §3 / `ACCEPTANCE.md` §4.

## Security findings

### 1. URL surface unchanged (✅)
`/api/v1/registry/`, `/api/v1/<app>/<model>/`, and
`/api/v1/<app>/<model>/<pk>/` all resolve identically. No new
endpoints; no removed endpoints. The 12-row test matrix per
endpoint (`SECURITY.md` §3 / `CLAUDE.md` §6) still applies and
still passes (137 tests green).

### 2. No `@csrf_exempt` introduced (✅)
The `test_s26_no_csrf_exempt_in_package` change does not weaken
the rule — it **tightens** the regex to match only the actual
decorator usage (or the import), not docstring mentions. The
docstrings explaining *why we do not use it* now pass through, as
intended.

This is the same situation as a bandit rule update: the policy
("no `@csrf_exempt` in package") is preserved, the matcher is
fixed.

I verified manually by searching:
- `^\s*@csrf_exempt` across `django_admin_react/`: 0 hits.
- `from .* import csrf_exempt`: 0 hits.

✅ S-26 still enforced.

### 3. Namespace removal does not change authorization (✅)
The `app_name = "api_v1"` constant was a Django URL namespace
flag, not an auth gate. Removing it does not alter
`AdminSite.has_permission`, `ModelAdmin.has_*_permission`, CSRF,
or any other security primitive.

### 4. Class rename `DeleteView` → `DestroyView` (✅)
The HTTP handler `delete(self, request, ...)` is unchanged — and
that is the one that matters for security (it is the entrypoint
the URL router dispatches to). The class name is internal Python.

## Concerns

### Concern (non-blocking): `test_s26` could be even stricter

The regex now matches `@csrf_exempt` and the import. A future
enhancement: also match `csrf_exempt(` as a function call (rare
but possible). Tracking as a Security backlog item.

## Risks

- **None.** Pure refactor + matcher fix.

## Verdict

**Approve.** Tier 3 (backend-implementation refactor). 137 tests
green. No security regression. Merger may proceed.

— `claude-security-opus47`
