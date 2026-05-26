# Security review — Architect PR #14 `feat/pnpm-script-runner`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (Security)
PR branch: `feat/pnpm-script-runner`
Tip commit: `ad124c3 feat(tooling): pnpm script runner + rename frontend/packages/shell → apps/web`
Author: `claude-architect`

Per the 3-reviewer rule, this is the Security role-specific review.

---

## Scope I checked

- `package.json` (root) — scripts surface.
- `scripts/dev.sh` — auto-superuser creation logic in DEBUG mode.
- `frontend/apps/web/` — package rename, no new code.

## Security findings

### 1. `scripts/dev.sh` auto-superuser is gated on DEBUG (✅)
The script creates a superuser only when `DEBUG=1` is set. This is
the right gate; production-shaped configs won't accidentally bake
an `admin/admin` account. The username/password are documented
non-secrets used only for the demo project.

### 2. No new endpoints, no new settings, no new deps (✅)
The pnpm scripts wrap existing Poetry / pytest / pnpm-workspace
commands. No new attack surface.

### 3. `package.json` is a frontend root file — Tier 5

Per `CLAUDE.md` §3 and `docs/agents/autonomy-policy.md`, changes
to the frontend root `package.json` dependencies are Tier 5
(human-review-only). This PR only adds **scripts**, not
dependencies. The `devDependencies` block in `package.json` is
empty. Confirmed not a Tier 5 change.

### 4. `scripts/dev.sh` uses `set -euo pipefail` (✅)
Stops on errors / undefined vars / pipe failures. Avoids partial
state if a step fails mid-bootstrap.

## Concerns

### Concern 1 (non-blocking): `dev.sh` `--debug` is the default

Calling `pnpm run dev:fintech` always sets `DEBUG=1`. If a
contributor copy-pastes the script for non-demo use, DEBUG could
linger. Mitigation: comment in `dev.sh` already states "this script
is for local development only; do not invoke in production".
Acceptable.

### Concern 2 (non-blocking): no audit step in `dev.sh`

The script bootstraps a demo without running `audit-deps.sh`
first. For a demo, that's fine. Recommend a future PR have
`scripts/audit-deps.sh` (Security PR #15) be a documented
pre-launch step.

## Risks

- **Low.** No new code paths, no new endpoints, no exempt CSRF,
  no settings drift.
- The "demo superuser" pattern is the standard Django bootstrap;
  documented and gated.

## Verdict

**Approve.**

No security regressions. The PR adds developer ergonomics
(`pnpm run dev:<example>`) without altering the runtime contract
or the linter stack. The Merger may proceed.

— `claude-security-opus47`
