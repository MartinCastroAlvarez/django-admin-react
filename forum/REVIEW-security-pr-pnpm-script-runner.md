# Security review — PR `feat/pnpm-script-runner`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (delegated by PM session for review-gathering cycle)
Tier: would have been 4 (frontend / build pipeline, root `package.json` is
script-only with no `dependencies` block)
Tip commit: `ad124c3 feat(tooling): pnpm script runner + rename
frontend/packages/shell → apps/web`
Author: `claude-architect`

## Status

**Already merged into `main` via PR #14** (`cd0a37b feat(tooling): pnpm
script runner + rename frontend/packages/shell → apps/web (#14)`).
`origin/main:package.json` is byte-identical to
`origin/feat/pnpm-script-runner:package.json`.

## §5.1 [S]-checklist (audit record, brief)

- [x] **[S]** No secrets / tokens / PEMs / `.env` content. ✅
- [x] **[S]** No `Model.objects.*` in `django_admin_react/`. The
      `scripts/dev.sh` script does `User.objects.filter(...)` /
      `User.objects.create_superuser(...)` against the **example
      project**, gated by `DJANGO_DEBUG != 0` (refuses to seed
      defaults in non-dev) — outside the package, so B-2 does not
      apply. ✅
- [x] **[S]** No `csrf_exempt`, no perm weakening. ✅
- [x] **[S]** No frontend `@dar/api` import from page packages. ✅
      (only package renames; `frontend/packages/shell` →
      `frontend/apps/web`, `name: @dar/web`)
- [x] **[S]** No model-specific names in `django_admin_react/` or
      `frontend/packages/`. The `dev.sh` banner mentions `Account`,
      `Book`, etc., **inside the bash script** (not in
      `django_admin_react/` or `frontend/packages/`). The CLAUDE.md
      §7 ban is scoped to package / frontend code; allowed in dev
      scripts. ✅
- [x] No `# noqa` on a security rule. ✅
- [x] No tests skipped/xfailed. ✅
- [x] No new third-party Python dep without decisions entry. ✅
- [x] No new third-party npm dep in a generic package
      (`@dar/ui`, `@dar/api`, `@dar/data`). Root `package.json` has
      **no `dependencies` or `devDependencies` block** — it is a
      script-runner manifest only; the only third-party reference is
      to `pnpm` itself via `engines`. ✅
- [N/A] No code changes that need contract doc updates.

## Threats noted (already-merged, so post-hoc)

1. **Default-dev superuser credentials `admin / admin`.** The script
   refuses to seed defaults if `DJANGO_DEBUG=0`, prints them in the
   banner with "DEV ONLY — never use these creds anywhere else", and
   they live only in the consumer's local example DB. Acceptable for
   the example project.
2. **`pnpm run deploy` shells `scripts/deploy.sh`.** That script is
   separately reviewed (Tier 5 / Tier 6 territory); not part of this
   branch.

## Verdict

**Approve (already merged — close branch).**

Tier-4 surface, no security-blocking findings. Merger action: close
the open PR with "already merged" and delete the remote branch.

— `claude-security-opus47`
