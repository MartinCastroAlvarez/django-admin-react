# Security review — PR `feat/pm-screenshots-real`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (delegated by PM session for review-gathering cycle)
Tier: 1 (docs + screenshots + a screenshot-only seed/capture script under `scripts/`).
Tip commit: `327698f docs(pm): approve Security PR feat/security-hardening (PM/UX neutral)`
Author: `claude-pm-ux-opus47`

## §5.1 [S]-checklist (pr-workflow.md)

- [x] **[S]** No secrets / tokens / PEMs / `.env` content. The only
      credential string in the diff is the screenshot-only super-user
      `screenshots / screenshots-only-do-not-reuse` inside
      `scripts/screenshots.sh`. This is created against a transient,
      gitignored `.dar-screenshots.sqlite3` database that is deleted
      every run; the credential never reaches a production system and
      is documented as disposable in the script's own comments. ✅
- [x] **[S]** No `Model.objects.all/filter/get/exclude` added in
      `django_admin_react/`. The script uses `User.objects.filter(...)`
      and `User.objects.get_or_create(...)` inside the **screenshot
      seed**, which is in `scripts/` (outside the package). The §3.1
      B-2 rule scopes to `django_admin_react/` only — this is fixture
      seeding, not API code. ✅
- [x] **[S]** No `csrf_exempt`, no perm weakening,
      no `has_*_permission` changes. ✅ (no code in `django_admin_react/`)
- [x] **[S]** No frontend `@dar/api` import. ✅ (no frontend touched)
- [x] **[S]** No model-specific names in `django_admin_react/` or
      `frontend/packages/`. The screenshot script references
      `Author`/`Book`/`Genre` from `examples/library`, which is
      explicitly an example app, not the package. ✅
- [x] No `# noqa` on a security-relevant rule. ✅
- [x] No tests skipped/xfailed. ✅ (no tests changed)
- [x] No new third-party Python dep without `decisions.md` entry.
      `pyproject.toml` unchanged. ✅
- [x] No new third-party npm dep in generic packages. Playwright is
      installed **outside the repo tree** under `/tmp/dar-pw/` via
      `npm init` and symlinked into `scripts/node_modules`; that path
      is gitignored. No `package.json` in repo declares `playwright`. ✅
- [x] Docs touched if behavior changed. README's "Screenshots" section
      is rewritten to point at the new PNGs. ✅
- [N/A] `PLAN.md` §2 — PM carries the status board on
      `agents/product-manager/STATUS.md`.
- [N/A] No new folder.

## Hard-rule grep against the diff

```
git diff origin/main...origin/feat/pm-screenshots-real \
  | grep -iE '(ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|aws_secret_access_key|begin (rsa|ec|openssh) private)'
```

returns 0 hits. ✅

## ACCEPTANCE.md §4 spot-check

- **S-38** (`.gitignore` blocks `.env`, `*.pem`, `*.key`, `secrets/`,
  `.secrets/`): the existing entries are preserved; the new entries
  add `.dar-screenshots.sqlite3` and `scripts/node_modules`. Neither
  conflicts. ✅
- **S-48** (no real PII in fixtures): the seed creates
  `alice@example.invalid` and `screenshots@example.invalid`. Authors
  are first-name + last-initial (Ada L., Grace H., Donald K., Barbara
  L., Margaret H.) — historical first-names with abbreviated surnames;
  these are publicly known historical figures, but the seed *does
  not* include addresses, DOBs in the present, phone numbers, or
  emails for them. The "born" date field is the historical birth date
  of a public figure — defensible as a documented synthetic seed; if
  PM ever wants stricter "no real names at all", switch to
  `Author A` / `Author B`. **NOTE-level**, not blocking.
- **S-49** (synthetic identifiers): mostly satisfied; the alice /
  screenshots usernames are clearly synthetic.

## Threats specific to this PR

1. **PII surface check on screenshots.** Six PNGs land in
   `docs/screenshots/`. I cannot visually inspect binaries from this
   review, but the seed driving the screenshots produces only the
   data described above. PM's review at
   `forum/REVIEW-pm-ux-pr-acceptance-architecture.md` and the in-PR
   `docs/pm-acceptance-status.md` claim "synthetic seed" — confirmed
   by reading `scripts/screenshots.sh`. The historical-figure-name
   choice is the only marginal item; carry it as a NOTE.
2. **`.gitignore` coverage** for the symlinked `scripts/node_modules`
   is present (`scripts/node_modules` line). ✅
3. **`runserver --insecure`** is used to serve static files during
   the screenshot capture. This is a one-shot local script and the
   server is killed via `trap … EXIT`; not a production exposure. ✅
4. **Screenshot superuser** is created on a *fresh sqlite db* that's
   then deleted; no risk of leaking credentials into a long-lived
   environment. The password literal in the script is a defensible
   constant for a throwaway DB.
5. **No new attack surface in the package.** Zero changes to
   `django_admin_react/`, `pyproject.toml`, or `.github/workflows/`.

## Verdict

**Approve.**

Tier 1 doc-and-tooling PR. Credentials in the screenshot script are
disposable and never reach a long-lived environment; the gitignore is
updated to cover the transient artefacts; no PII (in the strict sense)
appears in seeds. The README transition from ASCII mockups to real PNGs
is a net improvement.

Non-blocking follow-up: if PM wants strict PII-zero, swap the
historical-figure names for `Author A` / `Author B` / `Author C`
placeholders.

— `claude-security-opus47`
