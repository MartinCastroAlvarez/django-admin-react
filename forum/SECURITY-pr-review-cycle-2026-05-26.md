# Security PR review cycle — 2026-05-26

Reviewer: `claude-security-opus47` (delegated by PM session)
Branch carrying these reviews: `chore/security-pr-reviews-2026-05-26`

This index summarises the Security role's verdict on every open PR
flagged by the kickoff brief. Reviews are docs-only; nothing in the
package or any security-sensitive file has been edited by this
session.

## Summary table

| Branch                                             | Tier | Verdict                  | Notes                                                                          |
| -------------------------------------------------- | ---- | ------------------------ | ------------------------------------------------------------------------------ |
| `feat/backend-list-detail-endpoints`               | 3    | Approve                  | [S]-checklist clean. Two NOTE-level follow-ups.                                |
| `feat/backend-write-endpoints`                     | 3    | Approve                  | [S]-checklist clean. Stacks on list/detail. CSRF/auth code unchanged.          |
| `feat/pm-screenshots-real`                         | 1    | Approve                  | Screenshot creds are disposable; `.gitignore` covers transient artefacts.      |
| `feat/pm-durable-state-refresh`                    | 1    | Approve                  | Pure markdown PM state refresh.                                                |
| `feat/acceptance-criteria-engineering`             | 1    | Approve (already merged) | Subsumed by PR #11; close branch.                                              |
| `feat/security-state-and-coordination`             | 1    | Cannot review (self) + already merged | Self-review forbidden; PR #11 already shipped the content.        |
| `feat/security-hardening`                          | **5**| Cannot review (self) + defer to human | Touches `SECURITY.md` → human-only; self-review forbidden.        |
| `feat/architect-testing-md-and-api-contract`       | 1    | Approve (already merged) | Subsumed by PR #13; close branch.                                              |
| `feat/pnpm-script-runner`                          | 4    | Approve (already merged) | Subsumed by PR #14; close branch.                                              |
| `chore/foundation-pr1-opus47`                      | —    | Defer / close stale      | Subsumed by PR #1 + PR #7. See stale-triage file.                              |
| `pr/03-registry-endpoint`                          | —    | Defer / close stale      | Registry endpoint already on `main`.                                           |
| `feat/pm-screenshots`                              | —    | Defer / close stale      | Superseded by `feat/pm-screenshots-real`.                                      |
| `feat/pm-product-docs-v2`                          | —    | Defer / close stale      | Subsumed by PR #12.                                                            |

## Buckets

### Approve (ready to merge with PM + Architect co-review)

- `feat/backend-list-detail-endpoints` — Tier 3, needs one more
  non-author agent approval (Architect).
- `feat/backend-write-endpoints` — Tier 3, needs one more
  non-author agent approval (Architect).
- `feat/pm-screenshots-real` — Tier 1, ready as soon as PM count
  reaches the threshold.
- `feat/pm-durable-state-refresh` — Tier 1, ready.

### Defer to human (tier 5)

- `feat/security-hardening` — touches `SECURITY.md`. Human approval
  via GitHub UI before any merge, regardless of agent reviews.

### Cannot review (self-authored)

- `feat/security-state-and-coordination` — already merged via PR #11.
- `feat/security-hardening` — see above; also tier 5.

### Close as stale / subsumed

- `feat/acceptance-criteria-engineering`
- `feat/security-state-and-coordination`
- `feat/architect-testing-md-and-api-contract`
- `feat/pnpm-script-runner`
- `chore/foundation-pr1-opus47`
- `pr/03-registry-endpoint`
- `feat/pm-screenshots`
- `feat/pm-product-docs-v2`

## Non-blocking follow-ups (after the merge wave)

1. **End-to-end denylist test.** Add a `tests/test_security.py`
   case that wires a synthetic model with `password` / `api_key`
   fields through GET detail and POST/PATCH endpoints and asserts
   neither serialization nor write of those names is possible.
   Closes ACCEPTANCE.md §4.7 S-31 verification gap.
2. **`Cache-Control` on 200 responses.** List and detail 200s do not
   set `Cache-Control: no-store`. Write endpoints do. Bring list /
   detail in line for symmetric defence against shared caches.
   Closes ACCEPTANCE.md §4.6 S-30 (extension).
3. **`ghp_…XYZ` literal in `ACCEPTANCE.md` §4.8 S-37** will trip
   future secret-scanner runs. Rewrite as `<gh-prefix>…<hex>` or
   fence in a code block.

## Hard rules I observed

- No code outside `forum/` was touched.
- No real token, secret, PEM, `.env` content, or PII appears in any
  review file. The screenshot-script credential is referenced by
  filename only.
- All commits via `git -c commit.gpgsign=false commit` (per kickoff).
- No `gh pr *` calls made.

— `claude-security-opus47`
