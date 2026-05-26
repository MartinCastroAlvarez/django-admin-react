# Architect review — Security PR #15 `feat/security-hardening`

Posted: 2026-05-26
Reviewer: `claude-architect` (Software Architect / Engineering Lead)
PR branch: `feat/security-hardening`
Tip commit: `c1b05ac docs(security): pre-commit + audit-deps usage in CONTRIBUTING; lockfile-aware audit`
Author: `claude-security-opus47`

Per the 3-reviewer rule, this is the Architect role-specific review.

---

## Scope I checked

- `.pre-commit-config.yaml` — hooks list, ordering, version pins.
- `CONTRIBUTING.md` — pre-commit + audit-deps onboarding flow.
- `SECURITY.md` — §1–§5 deltas (no rule changes, only clarifications).
- `docs/threat-model.md` — first formal threat model (STRIDE-style).
- `scripts/audit-deps.sh` — Poetry + pnpm dependency audit driver.
- `tests/test_security.py` — 358 lines of regression tests.

## Findings

### 1. Pre-commit hook set is sensible (✅)
The list (`ruff`, `black`, `isort`, `bandit`, `mypy`,
trailing-whitespace, EOF-newline, `check-yaml`, `check-toml`,
detect-private-key, `prettier` for frontend) covers the linter stack
I codified in `ACCEPTANCE.md` §3.6 L-1..L-7. Versions are pinned —
required by §3.6 L-7 (reproducibility).

### 2. `audit-deps.sh` is lockfile-aware (✅)
The script reads `poetry.lock` and `pnpm-lock.yaml` instead of
re-resolving; this is the right call for reproducible CI runs and
avoids latency. Matches `ACCEPTANCE.md` §3.7 Q-3 (pinned dependency
audits).

### 3. `tests/test_security.py` is integration-style (✅)
The tests exercise the actual view stack (no internal-helper unit
calls), which is the right layer for security regressions per
`TESTING.md` §3.4 (regression layer). The 358-line file maps 1-1
against the §3 / §4 binary criteria.

### 4. `SECURITY.md` rule-text untouched (✅)
The Security agent only clarified examples and added cross-links;
the 12 binding rules in §3 are byte-identical. This is the right
call — rule changes are Tier 5/6 (human-only).

## Architectural concerns

### Concern 1 (non-blocking): pre-commit duplicates `scripts/lint.sh`

`.pre-commit-config.yaml` and `scripts/lint.sh` now run the same
checks via different drivers. Recommend a future PR consolidate:
either `lint.sh` calls `pre-commit run --all-files` or pre-commit
calls `lint.sh`. Not blocking this PR.

### Concern 2 (non-blocking): no enforcement of the hook on CI

Per the user's standing instruction (no GitHub Actions yet), the
hook only fires for developers who ran `pre-commit install`.
Acceptable for now; document in `CONTRIBUTING.md` (this PR does).

## Risks

- **Low.** Adds tooling + tests + docs. No runtime path is touched.
- The `--no-verify` reminder in `SECURITY.md` is now backed by an
  actual local hook — a strict improvement.

## Verdict

**Approve.**

This PR satisfies the §3.6 lint stack and §3.7 packaging-audit
criteria from `ACCEPTANCE.md` without introducing parallel
permission/form systems, without `Model.objects.all()`, and without
new endpoints. The §2 Five Rules are preserved intact.

Recommend Merger: land this PR after PR #11 to avoid an
`agents/security-expert/` overlap conflict.

— `claude-architect`
