# PM/UX next steps

Queue of the next things to do. Per [`AGENT.md`](AGENT.md) §11, move
completed items to [`DECISIONS.md`](DECISIONS.md) (with rationale) and
keep this list short.

Last-updated: 2026-05-26.

---

## 1. Immediate — awaiting other lanes (no PM/UX action)

- [ ] PR #79 — re-review by Architect / Security after realign push; then Tier 5 human merge.
- [ ] PR #94 — review by any non-PM agent; then Tier 5 human merge.
- [ ] PR #100 — Security review (PM/UX comment-approve already posted).
- [ ] PR #102 — review by any non-PM agent (Tier 1).
- [ ] PR #104 — review by any non-PM agent (Tier 1).
- [ ] PR #105 — review by any non-PM agent (Tier 1).

## 2. Backlog — PM/UX-owned, blocked

Frontend acceptance audit when SPA implementation lands for each
shipped backend feature:

- [ ] N-5 modal flow (depends on a SPA PR consuming PR #79).
- [ ] N-6 list_filter sidebar + chip row (depends on a SPA PR consuming PR #99).
- [ ] N-7 date_hierarchy drill-down (depends on a SPA PR consuming PR #80).
- [ ] E-6..E-12 SPA-side implementations.
- [ ] V-5 / V-6 / V-7 dark mode (depends on a SPA PR consuming PR #102's theming.md).
- [ ] R-6..R-10 mobile patterns (depends on a SPA PR consuming PR #102's responsive.md §9).
- [ ] I-1..I-6 PWA installability (depends on a SPA PR consuming PR #102's pwa.md).
- [ ] Issue #87 (screenshots): trigger capture work once dark-mode + mobile + PWA SPA implementations are sufficient to render at least the 6 baseline screenshots.

## 3. Backlog — PM/UX-owned, ready

- [ ] Periodic GitHub sweep at each session start (per `AGENT.md` §9.5.2).
- [ ] Triage any new user-agent-filed issues with the per-lane / acceptance-signal pattern from the prior 12.
- [ ] Author the v0.1.0 stable release verdict (Discussion in the "Announcements" category) once all v0.1.0 stable blockers from [`STATUS.md`](STATUS.md) §3 are ✅.

## 4. Open architectural questions PM/UX is parked on

None. The 2026-05-26 sprint resolved every PM/UX-side architectural question through PR review comments and issue triage.

## 5. Hand-off — to non-PM agents

- **Frontend lane (when active)**: the v0.2 UX contracts in `docs/ux/theming.md`, `pwa.md`, `responsive.md` §9 (all in PR #102 once it merges) are the source of truth. Issues #84/#85/#86 carry the tracking; cards on the [Project board](https://github.com/users/MartinCastroAlvarez/projects/3) are at Todo waiting for an author.
- **Architect lane**: PR #79's `RESERVED_TOP_LEVEL_PATHS` ask is tracked under issue #93 for the implementation slot.
- **Security lane**: PR #100 needs your review; issues #88/#89 are the in-flight follow-ups to PR #99.

Whoever picks any of the above up should claim the card on the Project board first and post a claim comment on the issue.
