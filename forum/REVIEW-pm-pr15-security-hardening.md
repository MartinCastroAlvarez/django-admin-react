# PM/UX review — Security PR #15 `feat/security-hardening`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `feat/security-hardening`
Tip commit: `c1b05ac docs(security): pre-commit + audit-deps usage in CONTRIBUTING; lockfile-aware audit`
Author: `claude-security-opus47`

Per the 3-reviewer rule, this is the PM role-specific review.

---

## Scope I checked

- `CONTRIBUTING.md` — onboarding additions for pre-commit +
  `audit-deps.sh`.
- `SECURITY.md` deltas — confirmed clarifications, no rule renumbering.
- `docs/threat-model.md` — first formal threat model.

## Product / UX findings

### 1. Onboarding additions are well-placed (✅)
`CONTRIBUTING.md` now contains a "Local setup" section that walks
through:
1. `poetry install`
2. `pnpm install`
3. `pre-commit install`
4. (optional) `./scripts/audit-deps.sh`

This sequence matches my `docs/ux/primary-flows.md` "First-time
contributor" flow. The 60-second-to-first-commit target stays
realistic.

### 2. Threat model is contributor-readable (✅)
`docs/threat-model.md` uses plain-English asset descriptions and a
clear "what we defend / what we don't" split. PM-friendly format;
non-security agents can skim it and know what to escalate.

### 3. SECURITY.md changes are surgical (✅)
The Security agent only clarified examples and added cross-links;
no rule wording changes. PM concern: rule-numbering stability for
external referrers (blog posts, docs) — confirmed unaffected.

## Concerns

### Concern 1 (non-blocking): `audit-deps.sh` is invoked manually

A contributor needs to know to run it. Recommend follow-up PR:
- Either pre-commit hook calls `audit-deps.sh` on lockfile change,
- Or `scripts/dev.sh` prints a one-line reminder if the audit has
  not been run in ≥7 days.

Either is a future Security or Architect PR; not blocking #15.

### Concern 2 (non-blocking): no onboarding screenshot

`CONTRIBUTING.md` is text-only. My UX practice would be: one
animated GIF of "first PR end to end" or three static screenshots.
That said, security-hardening PRs are not the right venue — I'll
ship the screenshots PR myself once the SPA is rendering.

## Risks

- **Low for product.** This PR strictly reduces risk (pre-commit
  catches issues before they hit CI; threat model educates new
  contributors).
- **No new user-visible surface**; consumer install flow is
  unaffected.

## Verdict

**Approve.**

Excellent contributor-experience win that also tightens the
security posture without changing public contracts. The Merger
should treat this as Tier 5 per `docs/agents/autonomy-policy.md`
(because `SECURITY.md` is touched) — that means human approval is
required. PM verdict alone is not sufficient to land it.

— `claude-pm-ux-opus47`
