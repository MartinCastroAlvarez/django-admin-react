# Architect review — PR `feat/pnpm-script-runner`

Posted: 2026-05-26
Reviewer: claude-architect (delegated by PM session for review-gathering cycle)
Tier: was 4 (frontend) when open; now moot
Tip commit: `ad124c3 feat(tooling): pnpm script runner + rename frontend/packages/shell → apps/web`

## Status: **MERGED to main** (PR #14)

`cd0a37b feat(tooling): pnpm script runner + rename frontend/packages/
shell → apps/web (#14)` is on `main`. The `frontend/apps/web/`
directory, `scripts/dev.sh`, and the root `package.json` all exist on
main now. `ARCHITECTURE.md §5.1` was updated in the same squash (the
"shell" naming was reconciled).

`origin/feat/pnpm-script-runner` still exists at the pre-squash SHA
`ad124c3` and would mass-delete if naively merged.

## §5.1 retrospective

I had earlier flagged this as a Tier 5 surface change (top-level
`package.json` deps + `ARCHITECTURE.md §5.1` rename). The squash-
merge happened with what I assume was the appropriate human review;
the merged commit on main updates `ARCHITECTURE.md` in lockstep with
the rename, which addresses my original concern.

## Verdict

**Close.** Content shipped via PR #14.

— claude-architect
