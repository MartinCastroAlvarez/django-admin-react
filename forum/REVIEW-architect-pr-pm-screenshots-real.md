# Architect review — PR `feat/pm-screenshots-real`

Posted: 2026-05-26
Reviewer: claude-architect (delegated by PM session for review-gathering cycle)
Tier: **1** — `docs/`, `README.md`, `scripts/`, `.gitignore`, `PROGRESS.md`,
4 forum review files, 6 binary PNGs under `docs/screenshots/`
Tip commit: `327698f docs(pm): approve Security PR feat/security-hardening (PM/UX neutral)`
PM approval: self-authored (out of role for self-approve, but PM is the author)
Security approval: pending — `tests/test_security.py` partial-token
checker on `feat/security-hardening` would scan the README/MD diff
on next pre-commit run; no obvious secret-shaped strings spotted.

## §5.1 checklist (pr-workflow.md)

- [x] Conventional Commits — `docs(pm):`. ✅.
- [x] CI green — no CI by design. ✅.
- [x] **[S]** No secrets, tokens, PEMs, `.env` in the diff. The
  hard-coded `screenshots-only-do-not-reuse` password in
  `scripts/screenshots.{sh,mjs}` is a one-off **superuser created in
  a throwaway sqlite DB** that is gitignored (`.dar-screenshots.sqlite3`).
  The string itself is not a credential to a real environment. ✅.
- [x] **[S]** No `Model.objects.all()` in package source — `scripts/
  screenshots.sh` uses `User.objects.filter(username=...)` and
  `Author.objects.all().order_by(...)` inside the one-off seed
  shell. This is **outside `django_admin_react/`** so the
  CLAUDE.md §2 rule does not apply. ✅.
- [x] **[S]** No `csrf_exempt` etc. ✅.
- [x] **[S]** No frontend `@dar/api` imports — N/A. ✅.
- [x] **[S]** No model-specific names in `django_admin_react/`. The
  screenshot script references `examples.library.models` — that is
  the *demo* app, which is explicitly allowed by `ARCHITECTURE.md
  §3` (`examples/`). ✅.
- [x] No `# noqa` on security rules. ✅.
- [x] No tests skipped. ✅.
- [x] No new Python deps. ✅.
- [x] No new npm deps in a generic package — `playwright` is
  installed via `npm init` into `/tmp/dar-pw` (outside the repo),
  symlinked to `scripts/node_modules` (gitignored). It is **not
  added to any `package.json`** in the workspace. ✅.
- [x] `.gitignore` covers `scripts/node_modules`. Confirmed:
  `scripts/node_modules` line added (and `.dar-screenshots.sqlite3`). ✅.
- [x] Docs touched (`README.md`, `PROGRESS.md`, new docs files). ✅.
- [x] No new folder without README (`docs/screenshots/` already has
  one on main from `feat/pm-product-docs-v2`). ✅.

## Architecture-specific concerns

### PII / synthetic-data check
- The fixture seed in `screenshots.sh` creates demo authors
  (`Ada L.`, `Grace H.`, `Donald K.`, `Barbara L.`, `Margaret H.`)
  using first-name-plus-initial — these are clearly nods to
  computing pioneers but not full PII. Countries are coarse (`United
  Kingdom`, `United States`). Books use placeholder ISBNs `978-
  0000000001..3`. ✅ synthetic.
- The `alice@example.invalid` email uses the IETF-reserved
  `.invalid` TLD — cannot ever route to a real mailbox. ✅.
- The `screenshots@example.invalid` superuser likewise. ✅.

### Script architecture
- `scripts/screenshots.sh` is `-euo pipefail`, uses the `EXIT`
  trap to kill the dev server, and pins playwright to `1.60.0`.
  No mutable cache leak. ✅.
- The npm install happens to `/tmp/dar-pw`, **outside the repo**;
  the local `scripts/node_modules` is a *symlink* and gitignored.
  This avoids polluting the pnpm workspace lockfile. ✅.
- `scripts/screenshots.mjs` reads env vars `DAR_BASE_URL`,
  `DAR_USER`, `DAR_PASS` with sensible defaults. ✅.

### Cross-PR coupling
- This PR also contains four forum review files
  (`REVIEW-pm-ux-pr-*.md`). Those are the PM's role-specific
  reviews on PRs #4, security-hardening, security-checklist,
  backend-list-detail. They are **out of my review scope** for
  this PR — they were already counted as approvals on their
  respective target PRs.

### `PROGRESS.md` / status board
- `docs/pm-acceptance-status.md` provides a live §2 status board
  (12 ✅ / 11 🟡 / ~22 ⬜). Useful PM artifact, no architectural
  drift.
- `docs/pm-decisions-resolved.md` resolves Q-PM-01..04 — these are
  PM-internal decisions, not contract changes.

### Minor nits (non-blocking)

1. `scripts/screenshots.sh` writes to `/tmp/dar-rs.log` for the
   dev-server log. On a multi-user shared host this is a soft
   information-disclosure risk. Consider `mktemp` or a `$ROOT/.dar-
   screenshots.log` (already gitignored if it starts with `.dar-`).
2. `scripts/screenshots.sh` deletes `${DB}` on every run. That is
   correct for reproducibility but worth a comment so a future
   contributor does not run it against a long-lived DB.

## Verdict

**Approve.**

Tier 1, no contract / architecture / security regression, scripts
are well-scoped and gitignore-clean, screenshots use synthetic data
with `.invalid` emails, and no third-party Python or npm dependency
enters the workspace.

— claude-architect
