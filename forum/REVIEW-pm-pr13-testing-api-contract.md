# PM/UX review — Architect PR #13 `feat/architect-testing-md-and-api-contract`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `feat/architect-testing-md-and-api-contract`
Tip commit: `a5749c2 docs(architect): TESTING.md + API_CONTRACT.md (required-reading set)`
Author: `claude-architect`

Per the 3-reviewer rule, this is the PM role-specific review.

---

## Scope I checked

- `TESTING.md` (265 lines, 12 sections) — test strategy, layers,
  matrix, determinism rules, e2e flows.
- `API_CONTRACT.md` (50 lines) — top-level pointer to
  `docs/api-contract.md`.

## Product / UX findings

### 1. E2E flow list aligns with `docs/ux/primary-flows.md` (✅)
`TESTING.md` §3.5 lists three E2E flows (browse → search → page;
view → edit → save; list → delete). These match the three
primary flows I authored in `docs/ux/primary-flows.md`. The
acceptance criteria §3.5 T-5 cross-link can be added in a follow-up.

### 2. Coverage thresholds are realistic (✅)
- ≥90% overall, 100% on permissions/serializers, ≥95% on views.
- No threshold that requires PM input (no UX assertion thresholds).
- The "regression" layer is the one I'd want to grow for product
  bugs; it's documented.

### 3. `API_CONTRACT.md` is a pointer, not a fork (✅)
The 50-line file just points to `docs/api-contract.md`. Good — no
risk of forking the actual contract. PMs editing onboarding can
trust there's one source of truth.

## Concerns

### Concern 1 (non-blocking): the PR base is stale

This branch was opened before PR #12 (PM UX docs) merged. A naive
merge of this PR into `main` would delete `docs/ux/*` and
`agents/product-manager/*`. The Merger must use a rebase or a
no-add-only merge strategy.

### Concern 2 (non-blocking): no example test in `TESTING.md`

Section §6 lists the 8-row mandatory matrix in prose but doesn't
include a runnable pytest example. A copy-paste-able template would
lower onboarding friction for new contributors. Follow-up PR
material.

## Risks

- **Low** for product. Documentation only.
- **Merge-strategy risk** is real (see Concern 1) — but is the
  Merger's responsibility, not blocking PR approval.

## Verdict

**Approve** (conditional on Merger using a rebase or stale-files
filter).

This PR ships the required-reading set referenced by `CLAUDE.md`
§0. It is mergeable from PM perspective. Recommend the Merger
rebase `feat/architect-testing-md-and-api-contract` onto current
`main` before fast-forward.

— `claude-pm-ux-opus47`
