# PM/UX review — Architect PR #14 `feat/pnpm-script-runner`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `feat/pnpm-script-runner`
Tip commit: `ad124c3 feat(tooling): pnpm script runner + rename frontend/packages/shell → apps/web`
Author: `claude-architect`

Per the 3-reviewer rule, this is the PM role-specific review.

---

## Scope I checked

- `package.json` (root) — pnpm scripts: `dev:<example>`,
  `build:<linter>`, `build`, `deploy`.
- `scripts/dev.sh` — boots demo Django project with auto-superuser.
- `frontend/apps/web/` (renamed from `frontend/packages/shell/`).
- README delta updates referencing the rename.

## Product / UX findings

### 1. `dev:<example>` matches the requested mental model (✅)
The user's spec was: "pnpm run dev:fintech runs the fintech
example." `package.json` wires this 1-1, and `scripts/dev.sh`
boots the example with an auto-superuser so a new contributor can
see the SPA in <30 seconds. This satisfies my own
`docs/ux/primary-flows.md` "First-run-on-localhost" flow.

### 2. The `apps/web` rename keeps future doors open (✅)
The user explicitly asked for `apps/web/` so that
`apps/mobile/` is reachable later. The rename matches that intent.
PM ROADMAP item "Phase 3: native shells" can now reference
`apps/mobile/` as a real path.

### 3. Onboarding text is updated in lockstep (✅)
Five README files (`CLAUDE.md`, `PLAN.md`, `PROGRESS.md`,
`frontend/README.md`, `scripts/README.md`) are touched to reflect
the rename. No stale `packages/shell` references remain.

## Concerns

### Concern 1 (non-blocking): the `deploy` script gates on a PyPI
token the user has not yet provided

`package.json` exposes `pnpm run deploy` but the underlying
`scripts/deploy.sh` will fail without `PYPI_API_TOKEN`. This is the
user's explicit gate: no deploy until they see screenshots + the
acceptance criteria pass. PM verdict: leave as-is; the user is the
release gatekeeper. Just document the gate in the README near the
"Deploy" section in a follow-up.

### Concern 2 (non-blocking): no `pnpm run dev` (no example) default

A `dev` script with no example name fails fast (good) but doesn't
print the available examples. Tiny UX win for a follow-up:
`pnpm run dev` could print "available examples: fintech, library,
hr, blog, cms".

## Risks

- **Low for product**, since the renaming is mechanical and no new
  user-facing surface is added.
- **Slight onboarding-doc risk**: the user's main README must list
  examples — fixing that is non-blocking and not in this PR.

## Verdict

**Approve.**

Strong PM win: matches the requested CLI shape, preserves the
`apps/mobile/` future surface, and the onboarding text is updated
consistently. Merger may proceed.

— `claude-pm-ux-opus47`
