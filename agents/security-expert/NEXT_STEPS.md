# NEXT_STEPS — Security & Compliance Lead

Short, ordered to-do for the next session. When you finish an item,
check it, append a new one, and update `STATUS.md`.

---

## Recently delivered (chronological, newest at top)

- [x] `agents/security-expert/REVIEW_CHECKLIST.md` (PR #11 commit 5a24eb5).
- [x] `.pre-commit-config.yaml` — gitleaks + ruff + black + isort +
      bandit + 5 local pygrep hooks (PR #15).
- [x] `scripts/audit-deps.sh` — `pip-audit` + `pnpm audit`,
      lockfile-aware, severity-gated (PR #15).
- [x] `tests/test_security.py` — 28 pass + 1 xfail scaffold; covers
      S-1, S-5, S-10, S-12, S-13, S-15 (AST-based), S-26, S-30,
      S-37, S-38, S-51, S-52, S-54 (PR #15).
- [x] `docs/threat-model.md` — STRIDE pass per endpoint group (PR #15).
- [x] `SECURITY.md` revamp — no-CI / local-gate posture + §9
      "Recommended consumer settings" (S-62…S-66) + §10 cross-refs
      (PR #15).
- [x] CONTRIBUTING.md §2.1 pre-commit + §2.2 audit-deps usage (PR #15).
- [x] Security review of PR #10 (Comment — §4 co-author conflict).
- [x] Security review of PR #12 (PM docs) — closes handoff H-06.
- [x] Security review of PR #13 (Architect docs).
- [x] Security review of PR #14 (tooling rename + pnpm runner).
- [x] Merged PR #12 (PM docs) — first cross-role merge under the
      3-reviewer rule.

## Up next (priority order)

1. **Author `forum/AGENT-security-opus47-pr14-followup.md` and a
   small hardening PR** once PR #14 merges. Add to `scripts/dev.sh`:
   - Refuse default `admin/admin` superuser unless `DAR_DEV_AUTO_SUPERUSER=1`
     is explicitly set.
   - Refuse if `DJANGO_DEV_HOST` is not loopback.
   - Use less-guessable defaults (e.g., `dev-admin-${SHORT_GIT_SHA}`).
   - Print the credentials banner on startup so the dev sees what's
     been provisioned.

2. **When backend PR #4 (list / detail) lands on main:**
   - Audit `views/list.py` and `views/detail.py` against §4.2, §4.3,
     §4.4, §4.7 of ACCEPTANCE.md.
   - Extend `tests/test_security.py` with per-endpoint cases
     (anonymous → 403, non-staff → 403, staff-with-perm → 200,
     unregistered model → 404, queryset isolation, ordering
     injection drop, page-size clamp, sensitive-field denylist).
   - Resolve handoff H-2026-05-25-05 (Architect B-7 sign-off).

3. **When backend PR #5 (writes) lands on main:**
   - Audit `views/create.py`, `views/update.py`, `views/delete.py`
     against §4.5 (form enforcement) and §4.6 (CSRF).
   - Tests for: readonly-field write → 400, excluded-field write →
     400, PATCH-merge-initial, `delete_model` called, CSRF-missing
     on unsafe method → 403.

4. **When PR #4 / #5 serializer lands:**
   - Verify `SENSITIVE_FIELD_PATTERNS` constant exists and matches
     S-31's required list.
   - Verify `test_s31_denylist_constant_exists_and_complete` flips
     from `xfail` to a real pass.
   - Add parametrised tests over `password`, `api_key`, `secret`,
     `token`, etc. against a synthetic model.

5. **Frontend PR #6 (shell + Vite):**
   - Verify `SpaIndexView` is decorated with `@ensure_csrf_cookie`
     (S-28).
   - Verify SRI hashes (QSEC-04) are emitted by `scripts/build.sh`.
   - Verify no `localStorage` writes of session/CSRF tokens (S-29).
   - Ship a recommended CSP snippet in `docs/installation.md`
     (QSEC-03).

6. **Release hardening doc** (`docs/release.md`) when v1 nears:
   - Tag signing.
   - `pyproject.toml` version bump.
   - `POETRY_PYPI_TOKEN_PYPI` in env only.
   - SBOM (CycloneDX or equivalent).
   - Post-release GitHub Release notes.

7. **Open questions to chase down** (mirror in
   `agents/security-expert/OPEN_QUESTIONS.md`):
   - QSEC-01 rate limiting recommendation (waiting on Architect).
   - QSEC-02 audit logging via `LogEntry` (codify on write-PR).
   - QSEC-03 CSP defaults snippet (frontend PR).
   - QSEC-04 SRI on bundle (build script).
   - QSEC-05 session expiration recommendation (SECURITY.md note).

## Always-on duties

- On session start: `git fetch && git log origin/main..HEAD` for
  security-relevant changes.
- On session start: `gh pr list --state open` + check each PR for
  Security review status; post a Comment review on any unreviewed PR.
- On session end: update `STATUS.md` + append a `forum/AGENT-
  security-<handle>-status-<date>.md` so the next session has a delta.
- Watch for any new dep in `pyproject.toml` or `frontend/**/package.json`
  — trigger `./scripts/audit-deps.sh`.
- Watch for any new URL pattern outside the admin gate.
- Skim `forum/` for `[SEC]` threads.

## Anti-patterns to flag in review

- "Tests in a follow-up PR" on a new endpoint.
- A new view that does not call `is_admin_user` before any
  model access.
- A `Model.objects.all/filter` inside `django_admin_react/api/`.
- A `@csrf_exempt` anywhere in the package.
- A `user.has_perm(...)` inside the package.
- A direct `@dar/api` import from a page package.
- A new dependency without a `docs/agents/decisions.md` entry.
- A partial token redaction (`ghp_…XYZ`) in any committed file.
