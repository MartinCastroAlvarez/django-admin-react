# Software Architect — next steps

Architect's working queue, ordered by priority. Completed items move
to [`DECISIONS.md`](DECISIONS.md) (when decisional) or are deleted
(when purely operational). [`STATUS.md`](STATUS.md) captures the
sprint-level snapshot; this file is the actionable to-do.

Last updated: **2026-05-26** by `claude-architect-opus47-2026-05-26-2`.

---

## Priority order (per repo-owner directive 2026-05-26)

> "When there are PRs open, reviewing and approving them is highest
> priority, so that when the 3 approvals are obtained, they can be
> merged. Next comes ISSUES, and then continuing with the project
> steps + looking at the discussion, and then working towards the
> acceptance criteria."

Concretely for the Architect lane:

1. **Sweep + review every open PR** at session start. Cross-role
   approval is gated on Author ≠ Reviewer ≠ Merger; the Architect
   lane is one of the three. Post `--comment`-as-approval with the
   role declaration + verdict + §5.1 checklist body
   (per [`docs/agents/product-manager/AGENT.md`](../product-manager/AGENT.md) §9.5.1).
2. **Triage every open issue** the Architect owns. P0 issues
   take precedence over P1 / P2. Issues that already have a triage
   thread from another lane only need an Architect comment if the
   architectural posture is non-obvious (read: don't comment-spam).
3. **Address open Discussions** that touch architecture or process
   — consumer-feedback drops, release announcements with
   architectural follow-ups, process-change announcements.
4. **Advance toward `ACCEPTANCE.md` §3** acceptance criteria —
   strategic work after the per-PR / per-issue / per-discussion
   sweep settles.

The same-login `--comment` pattern is the substantive approval
mechanism; GitHub's UI state ("REVIEW REQUIRED") will not flip
green, but the Merger session reads body verdicts, not UI state.

---

## 1. Immediate — Architect owes

- [ ] **S-CRIT-1 follow-up PR (M2M silent-wipe in `writes.py`).**
  Security flagged this in [#119](https://github.com/MartinCastroAlvarez/django-admin-react/issues/119). The
  `try / except: fallback = []` pattern in
  `merged_initial_for_update`'s M2M branch silently wipes the M2M
  during PATCHes that don't touch the field. Drop the `try/except`
  so a descriptor error propagates as 500 — much better than
  silent data loss. 5-line patch + a test that asserts the M2M
  raises a descriptor error → 500, not 200-with-empty-M2M.

- [ ] **PR #94 — request-changes on §2 (range wire shape).**
  Documented in the PR #94 review comment (Architect lane).
  Either author reframes §2 to "range types serialize via `str()`
  fallback in v1" (Option A — Architect-recommended) or lands the
  structured serializer first (Option B).

- [ ] **PR #102 — cache-vs-`no-store` reconciliation** in
  `pwa.md` §2.1 + acceptance row I-3 narrowing. Endorsed Security's
  Option B; author fixup needed.

## 2. Backlog — Architect-owned, ready

- [ ] **Inlines write-half** ([#54](https://github.com/MartinCastroAlvarez/django-admin-react/issues/54)). Read half shipped; write half
  needs the formset round-trip contract + tests. Tier 3.
- [ ] **Post-hoc audits on the 9 PRs in [#119](https://github.com/MartinCastroAlvarez/django-admin-react/issues/119)** — Security
  has filed CRIT-1; the remaining 8 PRs need Architect
  cross-review for queryset / form / permission posture even though
  they're already on `main`. Audit trail is the deliverable, not
  gating; document on the individual PR threads.
- [ ] **Resolve open-questions where defensible** — see
  [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) + the repo-wide
  [`docs/agents/open-questions.md`](../open-questions.md). Several
  entries have tentative directions that have de-facto been
  followed; promote them to `decisions.md`.

## 3. Backlog — Architect-owned, blocked

- [ ] **Structured `range` serializer + tests** — blocked on PR #94
  choice. If Option A lands, this is filed as a new Tier-3 issue.
- [ ] **Session-expiry implementation PRs** (backend emission +
  `<SessionGate />` in `@dar/data`) — blocked on PR #79 + #102
  merging.
- [ ] **Public-readiness audit** — repo-owner asked for a go /
  no-go on flipping the repo to public + reaching consensus with
  other agents in a Discussion. Tracked separately from the per-PR
  / per-issue sweep.

## 4. Open architectural questions Architect is parked on

- **Concurrent-agent isolation strategy.** Three agent sessions
  share the same working directory; reflog shows colliding
  checkouts. Decision needed: do Architect sessions adopt
  `git worktree` mandatorily, or do we coordinate via a session-
  start lock? Filed for cross-role discussion.

## 5. Hand-off — to other lanes

- **Security** — owes post-hoc audits on the 8 non-CRIT-1 PRs
  (per [#119](https://github.com/MartinCastroAlvarez/django-admin-react/issues/119)). Architect will cross-review each.
- **PM/UX** — once PR #102 merges with cache-vs-`no-store`
  reconciled, the I-3 acceptance row narrowing should land in
  `ACCEPTANCE.md` §2.13.
- **Frontend (any author)** — implementation PRs for
  `<SessionGate />`, mobile patterns R-6..R-10, dark-mode toggle,
  and the PWA SW are all unblocked once #79 / #102 merge.
