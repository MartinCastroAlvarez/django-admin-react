# PM/UX — NEXT STEPS

Ordered queue. Check items off as they land in a PR or are merged.
The **first unchecked item** is the next thing to do.

When something is done in a PR but not yet merged, mark `[~]`
(in flight) and note the branch.

---

## This PR (`feat/product-vision-and-ux`)

- [x] Forum claim: `forum/AGENT-pm-ux-opus47-claim.md`.
- [x] `PRODUCT_VISION.md`.
- [x] `ACCEPTANCE.md` §2 (Product / UX section, with reserved §3 / §4).
- [x] `DESIGN_SYSTEM.md`.
- [x] `agents/` handoff scaffold (`README.md`, `DECISIONS.md`,
      `OPEN_QUESTIONS.md`, `HANDOFF.md`).
- [x] `agents/product-manager/{AGENT,STATUS,DECISIONS,OPEN_QUESTIONS,NEXT_STEPS,SKILLS}.md`.
- [ ] `ONBOARDING.md` — five-minute install path + pitfalls.
- [ ] `ROADMAP.md` — v1 / v1.x / v2 user-facing.
- [ ] `docs/ux/README.md` — index.
- [ ] `docs/ux/principles.md`.
- [ ] `docs/ux/states.md` — loading / empty / error / optimistic.
- [ ] `docs/ux/navigation.md` — SPA nav + URL contract.
- [ ] `docs/ux/accessibility.md` — WCAG AA checklist.
- [ ] `docs/ux/responsive.md` — breakpoints + table-to-card rule.
- [ ] `docs/screenshots/README.md` — screenshot inventory contract.
- [ ] README UX audit + small tightening edits.
- [ ] `docs/agents/changelog.md` — append PR row.
- [ ] `docs/agents/decisions.md` — append PM-tagged entries.
- [ ] Run `bash scripts/lint.sh` locally; fix any warnings.
- [ ] `git push -u origin feat/product-vision-and-ux`.
- [ ] Surface to repo owner that the PR is ready for non-PM review.

## Next PR after this one

- [ ] **README UX audit, part 2** — propose a structural rewrite
      once the SPA actually renders something to screenshot.
- [ ] Triage Q-PM-01 / -02 / -03 / -04 with the Architect and (where
      relevant) Security.
- [ ] Define **example-app acceptance** — which `ModelAdmin`
      features each example demonstrates, and how they map to
      `ACCEPTANCE.md` §2.9 (extensibility UX) criteria.

## Standing work (not in any single PR)

- [ ] Review every open PR with UX impact; post review-only
      comments tied to `ACCEPTANCE.md` §2 criteria.
- [ ] Update `STATUS.md`, `DECISIONS.md`, `NEXT_STEPS.md` at the end
      of every session.
- [ ] Watch for "would-be-tier-5" UX-hostile changes (e.g., new
      required settings keys, new top-level URL adds).

---

> When this list grows past ~25 items, archive the completed ones
> to a section "## Done — <month>" at the bottom of the file.
