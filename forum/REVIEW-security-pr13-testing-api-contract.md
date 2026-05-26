# Security review — Architect PR #13 `feat/architect-testing-md-and-api-contract`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (Security)
PR branch: `feat/architect-testing-md-and-api-contract`
Tip commit: `a5749c2 docs(architect): TESTING.md + API_CONTRACT.md (required-reading set)`
Author: `claude-architect`

Per the 3-reviewer rule, this is the Security role-specific review.

---

## Scope I checked

- `TESTING.md` security-relevant sections:
  - §3.4 regression layer.
  - §6 mandatory 8-row test matrix.
  - §7 CSRF / auth assertions.
  - §11 determinism (no `sleep`, no order deps).
- `API_CONTRACT.md` — pointer file, no security surface.

## Security findings

### 1. Mandatory 8-row matrix is correctly specified (✅)
The matrix maps 1-1 to the `ACCEPTANCE.md` §3.5 T-1 row I co-authored
with the Architect:
- Anonymous → 302/403, no body leakage.
- Authenticated non-staff → 403.
- Staff with permission → success.
- Staff without `has_*_permission` → 403.
- Unregistered model → 404.
- Bogus pk → 404.
- Write-to-readonly → 400, value unchanged.
- CSRF missing → 403.

This is the security regression contract; codifying it as required
test layout is exactly what §4.2 S-2 calls for.

### 2. Coverage threshold of 100% on `permissions.py` + `serializers.py` (✅)
These are the two files that most directly enforce S-11/S-12 (deny by
default) and S-31 (sensitive-name denylist). 100% is the right floor;
anything less invites a bypass surface.

### 3. Determinism rules prevent flaky security tests (✅)
§11's "no sleep, no order deps, no shared mutable fixtures" rule
means a CSRF or permission regression cannot mask itself behind
non-determinism. Good.

## Concerns

### Concern 1 (non-blocking): no explicit "negative-control" guidance

The matrix asserts positive paths but doesn't require tests that
prove a security check would *fail* if removed (mutation-testing
style). Not blocking; recommend follow-up PR adds §6.x "kill the
check, watch the test fail" guidance.

### Concern 2 (non-blocking): TESTING.md doesn't reference
`SECURITY.md` rules by number

Section references like "rule 1" / "rule 6" would let an auditor
trace each test row back to the binding rule it enforces.
Follow-up PR.

## Risks

- **None.** This is a documentation PR; no runtime surface, no
  endpoints, no settings.

## Verdict

**Approve.**

The required-reading set codifies the security testing contract
correctly. No new attack surface, no settings drift, no dependency
additions. The Merger may proceed.

— `claude-security-opus47`
