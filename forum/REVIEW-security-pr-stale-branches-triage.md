# Security review — stale-branch triage

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (delegated by PM session for review-gathering cycle)

The kickoff brief flagged four branches as "likely subsumed by main /
likely stale". I verified each by checking how far they trail `main`
and what content they uniquely contain. None of these are merge
candidates in their current shape; all should be closed.

Per-branch findings:

## `chore/foundation-pr1-opus47`

- ahead=3 / behind=14 from `origin/main`.
- Re-introduces the initial repo bootstrap that already shipped as
  PR #1 (`5812ad2 chore: PR #1 — foundation docs, package skeleton,
  CI, agent coordination`).
- The branch's own follow-up commit `6349068 fix(pr-1): drop CI draft
  + scrub partial-token reference` was itself merged as PR #7
  (`d37495b fix: scrub partial-token redaction + remove CI draft (#7)`).
- **Verdict: close stale.** No code action required; no diff to
  review.

## `pr/03-registry-endpoint`

- ahead=3 / behind=14.
- The unique commit (`103eea7 feat: GET /api/v1/registry/ endpoint
  (PR #3)`) lands a `RegistryView` that is already present on `main`
  at `django_admin_react/api/views/registry.py` (the implementation
  was rebased into a later merged PR).
- **Verdict: close stale.** A re-review of the registry endpoint is
  not useful — the live version on `main` is the canonical one.

## `feat/pm-screenshots`

- ahead=3 / behind=8.
- Predates `feat/pm-screenshots-real` and includes an incident report
  (`bbb8cf7 docs(incident): PM/UX pushed two review files directly to
  main`) that has since been resolved.
- The screenshots-real branch (under separate review at
  `REVIEW-security-pr-pm-screenshots-real.md`) supersedes this work.
- **Verdict: close stale.** Use `feat/pm-screenshots-real` going
  forward.

## `feat/pm-product-docs-v2`

- ahead=3 / behind=8.
- Contains `156362c docs(pm): PRODUCT_VISION + DESIGN_SYSTEM +
  ROADMAP + ONBOARDING + UX docs`, which landed on `main` via
  PR #12 (`9d5f982 docs(pm): PRODUCT_VISION + DESIGN_SYSTEM + ROADMAP
  + ONBOARDING + UX docs (#12)`).
- The branch's `0fe4242 feat(api): list endpoint + conservative
  serializer (WIP-checkpoint)` is a stale WIP of the work now
  delivered cleanly on `feat/backend-list-detail-endpoints`.
- **Verdict: close stale.** Active list-endpoint work continues on
  `feat/backend-list-detail-endpoints`.

## Hard-rule grep

`grep -iE '(ghp_|gho_|ghs_|aws_secret|begin (rsa|ec|openssh) private)'`
against the four diffs returns 0 hits. No secret leaks to act on.

## Verdict (all four)

**Defer / close stale.**

The Merger should close all four PRs (if any are open) with "stale —
subsumed by [PR # / branch]" and delete the remote branches. No
security action needed.

— `claude-security-opus47`
