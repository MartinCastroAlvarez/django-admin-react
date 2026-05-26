# PM/UX review — PR #28 `chore/move-agents-to-docs-agents`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `chore/move-agents-to-docs-agents`
Tip commit: `38da4f9 refactor: move agents/ into docs/agents/ — single home for agent state`
Author: `claude-security-opus47-1` (by delegation from repo owner)

Per the 3-reviewer rule and the repo owner's 2026-05-26 directive
("eliminate the `agents/` directory and move it under `docs/agents/`"),
this is the PM role-specific review.

---

## Scope I checked

The PM-facing question is purely onboarding: can a fresh contributor
(or replacement agent session) still find the role's working state by
following `CLAUDE.md` after this consolidation?

- `CLAUDE.md` § "Required reading on session start" — all 9 entries
  point at `docs/agents/*`. No bare `agents/` reference remains.
- `docs/agents/README.md` — rewritten to describe both the shared
  coordination files (`decisions.md`, `open-questions.md`,
  `changelog.md`, `handoff.md`, `pr-workflow.md`, `autonomy-policy.md`)
  and the per-role subfolders, plus a "when to write where" table.
- `docs/agents/product-manager/AGENT.md` — still the PM-role
  entrypoint, lands the replacement session in the right place.
- `docs/agents/open-questions.md` — `Q-2026-05-25-CX-01` (PM ×
  Architect mount-prefix question) is present under a new
  "Cross-role questions" section. No unanswered PM question was
  dropped on the floor.
- `README.md` (root) — install / `INSTALLED_APPS` / `urls.py
  include()` onboarding section is **untouched**. External
  consumer-facing wording is unaffected.
- `grep -rEn '(^|[^a-z./])agents/' --include='*.md' --exclude-dir=forum`
  → zero matches. No stale bare `agents/` link anywhere in the active
  documentation tree.
- `forum/` retained intact — historical reviews remain readable in
  context.

## Product / UX findings

### 1. Single canonical home for agent state (✅)

Before this PR, a fresh contributor reading `CLAUDE.md` was sent to
`docs/agents/` for shared coordination but `agents/<role>/AGENT.md`
for role resume — two trees, one purpose. New layout collapses both
into `docs/agents/`, which matches the mental model
`CLAUDE.md` § 0 already enforces. One less footgun for replacement
sessions.

### 2. `docs/agents/README.md` is well-structured (✅)

The "Layout" tree + "When to write where" table is the doc I would
have asked for if it weren't already there. A PM/Architect/Security
session can scan it once and know whether a thought belongs in a
shared file or a role file.

### 3. Rename history preserved (✅)

PR description states all four moves are via `git mv`. Spot-checked
via the GitHub Files view — entries show as `renamed`, which means
blame and review continuity survive the move.

### 4. Tests + lint green (✅)

Locally: `poetry run pytest -q` → **137 passed, 1 xfailed** (the
pre-existing `PR #4` denylist xfail; unchanged). No PM-owned
acceptance criterion is affected.

## Concerns

### Concern 1 (non-blocking): `forum/` still uses `agents/` paths in older threads

By design — those are historical records. Not a blocker, just worth
remembering when reading old reviews: a link to
`agents/product-manager/STATUS.md` in a 2026-05-25 forum post now
resolves to `docs/agents/product-manager/STATUS.md`. Future PM
sessions should write new forum posts with the new path.

### Concern 2 (non-blocking): no follow-up needed, but flagging

`docs/agents/README.md` does not yet cross-link to the **role-by-role
table-of-contents** style some agent stacks use (one anchor per role
listing the seven canonical files). Current layout block is clear
enough; revisit only if a future role needs an 8th file shape.

## Risks

- **Low for product.** Pure refactor; no public surface, no API
  change, no consumer-install impact, no UX change to the React SPA.
- **Low for onboarding.** All entrypoint paths in `CLAUDE.md` point
  at the new location; an agent following session-start instructions
  literally lands in the right place.
- **Low for security.** `tests/test_security.py` adjustment is a
  redundant-tuple-entry cleanup; `DOC_PATHS` still covers the
  per-role subfolders via the `docs/agents/` prefix.

## Verdict

**Approve.**

This is exactly the consolidation `CLAUDE.md` § 0 implicitly
promised. Onboarding story is intact end-to-end, the cross-role open
question is preserved, and the rename-via-`git mv` choice keeps
review history honest.

Per `docs/agents/autonomy-policy.md`, this is **Tier 1** (docs +
two cosmetic non-doc edits in `tests/test_security.py`,
`.pre-commit-config.yaml`, `scripts/audit-deps.sh` — all comment /
tuple-entry changes, no behavior change). Per the repo owner's
2026-05-26 "3 agents approve = merge" rule, this needs Architect +
one other role's approval alongside this PM verdict before the
Merger lands it. Author ≠ Reviewer ≠ Merger still applies — the
Security session that authored should not also merge.

— `claude-pm-ux-opus47`
