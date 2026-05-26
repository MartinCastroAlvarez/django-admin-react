# PM/UX — STATUS

Last-updated: 2026-05-26
Active session id: `claude-pm-ux-opus47`
Branch: `feat/pm-screenshots-real` (PR open, awaiting Architect + Security)
Worktree: `/tmp/dar-pm-work` for screenshot PR; `/tmp/dar-pm-state`
for this durable-state PR.

## Current step

**Pause point.** Every PM/UX deliverable that does not require the
React SPA to exist is shipped or in review. The next §2 status flips
depend on engineering PRs landing:

- PR #4 (`feat/backend-list-detail-endpoints`) — **PM-approved**
  2026-05-26 in [`forum/REVIEW-pm-ux-pr-backend-list-detail.md`](../../forum/REVIEW-pm-ux-pr-backend-list-detail.md).
  Once merged, flips §2.2 D-1 and §2.9 E-1 to ✅ on the API side
  and unblocks E-3 / E-4 toward ✅ via PR #6 / #7.
- PR #6 + #7 (frontend SPA) — not yet open.

The PM role's next action is the periodic PR sweep + flipping
status as PRs merge.

## What this session shipped

Cumulative since 2026-05-25; commits on `feat/pm-screenshots-real`
unless noted:

- Real Playwright screenshots (`docs/screenshots/0[1-6]-*.png`)
  replacing ASCII mockups; `scripts/screenshots.{sh,mjs}` regenerate
  them deterministically against `examples/project/`.
- README updated: 2 × 3 image grid; no marketing fluff; install
  path unchanged.
- `docs/pm-acceptance-status.md` — live §2 status board (12 ✅,
  11 🟡, ~22 ⬜).
- `docs/pm-decisions-resolved.md` — Q-PM-01..04 resolved.
- `forum/REVIEW-pm-ux-pr-backend-list-detail.md` — PM/UX approval
  of PR #4.
- `forum/REVIEW-pm-ux-pr-security-checklist.md` — PM/UX approval
  of Security `REVIEW_CHECKLIST.md` PR.
- `forum/REVIEW-pm-ux-pr-security-hardening.md` — PM/UX approval
  of `feat/security-hardening` (neutral).
- `PROGRESS.md` — added "v0.1 PM / UX criteria lane" + screenshots
  inventory table.

## Blockers

- **gh CLI auth.** Local `gh` is authed against
  `<gh-cli-account>`, which can't see the repo. `git push`
  works via embedded PAT. PR ceremony (`gh pr create / review /
  merge`) requires the repo owner to switch `gh auth` or add the
  `<gh-cli-account>` as collaborator. Not blocking local work — reviews
  ship as `forum/REVIEW-*.md` files. Reported in
  [`NEXT_STEPS.md`](NEXT_STEPS.md) §B.
- **No frontend PR yet.** Most ⬜ §2 criteria need PR #6 / #7. PM
  cannot accelerate this; tracking only.

## Open questions (mine)

All four resolved 2026-05-26 — see
[`DECISIONS.md`](DECISIONS.md) §2026-05-26 batch. None open at PM
layer. Cross-role open questions tracked in
[`../OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md).

## Cross-role handoffs

- **H-2026-05-25-01:** Frontend must satisfy `ACCEPTANCE.md` §2.4 /
  §2.5 / §2.7 / §2.8 before v0.1. Still open; tracked.
- **H-2026-05-25-02 / -03:** Architect §3 + Security §4 — both
  landed (visible on `feat/acceptance-criteria-engineering` and
  `feat/security-state-and-coordination`). PM-approved.
- **H-2026-05-25-04:** E2E primary flows — RESOLVED. PM shipped
  `docs/ux/primary-flows.md` in PR #12.
- **H-2026-05-26-01:** Add `filters: [{name, label, type, choices?}]`
  to list response (Q-PM-03 resolution). Filed to Architect.

## Latest decisions (mine)

See [`DECISIONS.md`](DECISIONS.md). Highlights since 2026-05-25:

- **Q-PM-01** "before / after" pairs: resolved as **superseded** —
  legacy admin captures are de-facto "before"; SPA captures are
  "after"; no `compare/` subfolder.
- **Q-PM-02** `Cmd+K` palette: **deferred to v0.2.** v0.1 ships
  `/`-focus and arrow / Tab / Esc / Enter only.
- **Q-PM-03** `list_filter` in v0.1: **yes, narrow scope** —
  `BooleanField`, `choices`, and FK with ≤ 25 distinct values.
  Backend handoff filed.
- **Q-PM-04** Empty registry: **friendly EmptyState, not redirect.**

## Quick links

- [`AGENT.md`](AGENT.md) — entrypoint for a fresh session.
- [`SKILLS.md`](SKILLS.md) — workflow tips (worktree pattern,
  screenshot pipeline, no-direct-main commit rule).
- [`NEXT_STEPS.md`](NEXT_STEPS.md) — what the next session should
  do first.
- [`DECISIONS.md`](DECISIONS.md) — append-only PM decisions.
- [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) — now empty at PM layer.
- [`REVIEW_CHECKLIST.md`](REVIEW_CHECKLIST.md) — rubric for PM-side
  PR reviews.
- [`../HANDOFF.md`](../HANDOFF.md) — cross-role handoffs.
- [`../../docs/pm-acceptance-status.md`](../../docs/pm-acceptance-status.md)
  — live §2 status board.
