# Architect PR review cycle — 2026-05-26

Posted: 2026-05-26
Reviewer: claude-architect (delegated by PM session for review-gathering cycle)
Branch: `chore/architect-pr-reviews-2026-05-26`

This is the index for the Architect's role-specific reviews of every
PR currently open against `origin/main`. The PM session opened a
parallel set under `REVIEW-pm-ux-pr-*.md`; the Security session
opened a parallel set under `REVIEW-security-pr*.md`. This completes
the Architect lane.

I did not write any code, did not edit any tracked file outside
`forum/`, and did not merge or close any branch. The user's
directive was "review and get approvals in the forum until ready to
merge".

**Note**: PRs #11, #13, and #14 were squash-merged onto `main` while
this review was being drafted. The branches still exist on `origin`
at their pre-squash SHAs, so my reviews for those are now retro-
verdicts: "close branch; content already on main."

---

## Approved (ready for Merger)

| PR branch | Tier | Architect review file |
| --- | --- | --- |
| `feat/backend-list-detail-endpoints` | 3 | [`REVIEW-architect-pr-backend-list-detail-endpoints.md`](REVIEW-architect-pr-backend-list-detail-endpoints.md) |
| `feat/backend-write-endpoints` | 3 | [`REVIEW-architect-pr-backend-write-endpoints.md`](REVIEW-architect-pr-backend-write-endpoints.md) |
| `feat/pm-screenshots-real` | 1 | [`REVIEW-architect-pr-pm-screenshots-real.md`](REVIEW-architect-pr-pm-screenshots-real.md) |
| `feat/pm-durable-state-refresh` | 1 | [`REVIEW-architect-pr-pm-durable-state-refresh.md`](REVIEW-architect-pr-pm-durable-state-refresh.md) |

## Deferred to human (Tier 5)

| PR branch | Tier | Architect review file |
| --- | --- | --- |
| `feat/security-hardening` | 5 (touches `SECURITY.md`) | [`REVIEW-architect-pr-security-hardening.md`](REVIEW-architect-pr-security-hardening.md) |

Approve in spirit; cannot auto-merge. Human-only per
`autonomy-policy.md`.

## Close as already-merged (squash merged while review in flight)

| PR branch | Merged via | Architect review file |
| --- | --- | --- |
| `feat/acceptance-criteria-engineering` | PR #11 (`c074e3c`) | [`REVIEW-architect-pr-acceptance-criteria-engineering.md`](REVIEW-architect-pr-acceptance-criteria-engineering.md) |
| `feat/security-state-and-coordination` | PR #11 (`c074e3c`) | [`REVIEW-architect-pr-security-state-and-coordination.md`](REVIEW-architect-pr-security-state-and-coordination.md) |
| `feat/architect-testing-md-and-api-contract` | PR #13 (`3e2859f`) | [`REVIEW-architect-pr-architect-testing-md-and-api-contract.md`](REVIEW-architect-pr-architect-testing-md-and-api-contract.md) |
| `feat/pnpm-script-runner` | PR #14 (`cd0a37b`) | [`REVIEW-architect-pr-pnpm-script-runner.md`](REVIEW-architect-pr-pnpm-script-runner.md) |

## Close as stale / superseded

| PR branch | Reason | Architect review file |
| --- | --- | --- |
| `chore/foundation-pr1-opus47` | Already on main via squash | [`REVIEW-architect-pr-foundation-pr1-opus47.md`](REVIEW-architect-pr-foundation-pr1-opus47.md) |
| `pr/03-registry-endpoint` | Already on main; mass deletion if merged | [`REVIEW-architect-pr-pr03-registry-endpoint.md`](REVIEW-architect-pr-pr03-registry-endpoint.md) |
| `feat/pm-screenshots` | Superseded by `feat/pm-screenshots-real` | [`REVIEW-architect-pr-pm-screenshots.md`](REVIEW-architect-pr-pm-screenshots.md) |
| `feat/pm-product-docs-v2` | Already on main via #12 | [`REVIEW-architect-pr-pm-product-docs-v2.md`](REVIEW-architect-pr-pm-product-docs-v2.md) |

---

## Merge order recommendation (subject to Security)

With #11, #13, #14 already on main, the remaining queue is:

1. **`feat/backend-list-detail-endpoints`** (Tier 3) — first piece
   of real backend code. PM and Architect approvals in place;
   Security's cross-check of SECURITY.md §3 rule citations is
   recommended for the auto-merge gate. The Security session has
   already reviewed PR #17 (`feat/backend-write-endpoints`) per
   `REVIEW-security-pr17-write-endpoints.md`, so the eyes are
   warm.
2. **`feat/backend-write-endpoints`** (Tier 3) — stacked on #1.
   Merge after #1 lands.
3. **`feat/security-hardening`** (Tier 5, **human-only**). Bring a
   human after #1 and #2 land so `tests/test_security.py` asserts
   run against the merged code.
4. **`feat/pm-screenshots-real`** (Tier 1) — independent of the
   backend stack; can land any time PM finalizes.
5. **`feat/pm-durable-state-refresh`** (Tier 1) — independent;
   land any time.

— claude-architect
