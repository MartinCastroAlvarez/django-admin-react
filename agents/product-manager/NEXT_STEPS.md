# PM/UX — NEXT STEPS

Ordered queue. Check items off as they land in a PR or are merged.
The **first unchecked item** is the next thing to do.

When something is done in a PR but not yet merged, mark `[~]`
(in flight) and note the branch.

---

## A. The next concrete actions (do in this order)

1. **PR sweep.** Run `git fetch origin && git ls-remote --heads
   origin`. For every branch ≥ 1 commit ahead of main that does
   not yet have a `forum/REVIEW-pm-ux-pr-*.md` file, decide:
   - Does it touch `ACCEPTANCE.md` §2 surfaces (UX, docs,
     onboarding, screenshots, README)? **Full review.**
   - Otherwise neutral approval (one-page review).
2. **Watch for frontend PR #6 / #7** (`@dar/shell`, list page,
   detail page, `@dar/data`). When it lands:
   - Regenerate screenshots (`bash scripts/screenshots.sh`) to
     capture **registry / list / detail / mobile / dark / login**
     — the six tiles in [`docs/screenshots/README.md`](../../docs/screenshots/README.md).
   - Flip every ⬜ row in [`docs/pm-acceptance-status.md`](../../docs/pm-acceptance-status.md)
     that the SPA satisfies.
   - Walk §2.4 / §2.5 / §2.7 / §2.8 against the running SPA;
     anything failing is a PR-blocking comment.
3. **Watch for `feat/backend-list-detail-endpoints` to merge.**
   On merge, flip §2.2 D-1 and §2.9 E-1 to ✅ on the API side
   (already pre-marked in the status board); leave 🟡 for E-2 /
   E-3 / E-4 until SPA consumption lands.

## B. Standing duties

- **Periodic PR sweep** (every session, before any other work).
- **Update durable state** — refresh `STATUS.md`, `NEXT_STEPS.md`,
  `DECISIONS.md` at the end of every session per the repo owner's
  "continuously updated" directive.
- **Veto power.** Watch for changes that:
  - Add a *required* settings key beyond `INSTALLED_APPS` +
    `include()`. Block unless `ACCEPTANCE.md` §2.1 P-2 is updated.
  - Require React knowledge for Django-only consumers. Block per
    §2.2 D-3.
  - Replace `Lucide` with another icon set, or add emoji to UI.
    Block per `DESIGN_SYSTEM.md` §7.
  - Bypass Tailwind CSS-variable theming for runtime config.
    Block per Q-PM-* decision log.

## C. Known follow-up work (no fixed order)

- [ ] **`filters` field** on the list response (Q-PM-03 resolution).
      Handoff `H-2026-05-26-01` filed to Architect; PM should
      review the follow-up PR when it appears.
- [ ] **Dark-mode + SPA screenshots** — regenerate the six
      legacy-admin captures with the SPA versions once PR #6 / #7
      merges. Same script.
- [ ] **v0.1 CHANGELOG.** Draft when the release gate (§5) goes
      green. Frame it for *Django developers* not React developers.
- [ ] **README "screenshots" section refresh** — once SPA captures
      exist, drop the "legacy HTML admin — what the React UI
      modernises" framing and the `PR #6 / #7` note.
- [ ] **PR ceremony unblocking** — when the repo owner resolves
      gh auth, switch from `forum/REVIEW-*.md` files to real GitHub
      PR reviews.

## D. Pause-point hygiene before handing off

If a session has to abort:

1. Commit work-in-progress to your branch (don't lose pixels).
2. Push (the embedded PAT in `.git/config` still works for push).
3. Update **this file** + `STATUS.md` to reflect what's done /
   pending.
4. Drop a one-paragraph `forum/AGENT-pm-ux-opus47-status-<date>.md`
   describing the pause point and any open question.

---

> When this list grows past ~25 items, archive the completed ones
> to a section "## Done — <month>" at the bottom of the file.
