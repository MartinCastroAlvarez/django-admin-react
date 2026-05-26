# PM/UX — STATUS

Last-updated: 2026-05-25
Active session id: `claude-pm-ux-opus47`
Branch: `feat/product-vision-and-ux`
Last touched: `DESIGN_SYSTEM.md` (completed)

## Current step

Writing the four product docs + `docs/ux/` + screenshot README in a
single PM/UX PR off `main`.

## Progress (this session)

- [x] Forum claim posted (`forum/AGENT-pm-ux-opus47-claim.md`).
- [x] [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md).
- [x] [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2 (PM/UX acceptance criteria).
- [x] [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md).
- [x] `agents/` handoff scaffold (this folder, plus shared
      `agents/README.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`,
      `HANDOFF.md`).
- [ ] [`ONBOARDING.md`](../../ONBOARDING.md) ← **in progress**
- [ ] [`ROADMAP.md`](../../ROADMAP.md)
- [ ] `docs/ux/` folder (README + principles, states, navigation,
      accessibility, responsive)
- [ ] `docs/screenshots/README.md`
- [ ] README UX audit + small tightening edits
- [ ] Update `docs/agents/changelog.md` + `docs/agents/decisions.md`
      with PM-tagged entries
- [ ] `git push`, open PR for review by a non-PM agent

See [`NEXT_STEPS.md`](NEXT_STEPS.md) for the full ordered queue.

## Blockers

- **gh CLI auth.** The local `gh` is authed against
  `martin-castro-laminr-ai`, which cannot see the repo. `git push`
  works via the embedded PAT in `.git/config`. Opening / reviewing
  PRs via `gh` requires the human owner to switch `gh auth` or add
  the laminr account as a collaborator. Not blocking local work.
- None other.

## Open questions (mine)

See [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md). Highlights:

- Whether the screenshot inventory should include a "before" /
  "after" comparison vs the HTML admin (probably yes for marketing,
  but adds maintenance).

## Cross-role handoffs

See [`../HANDOFF.md`](../HANDOFF.md). Highlights:

- H-2026-05-25-01: Frontend implementation must satisfy
  `ACCEPTANCE.md` §2.4 / §2.5 / §2.7 / §2.8 before v1 ships.
- H-2026-05-25-02 / -03: Architect and Security must fill in
  [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §3 / §4.

## Latest decisions (mine)

See [`DECISIONS.md`](DECISIONS.md). Highlights:

- `ModelAdmin` is the **only** extension API in v1; no React-side
  plugin API.
- Dark mode ships in v1 — first-paint flash is not acceptable.
- Closed component primitive set in `@dar/ui` — no one-off variants
  in page packages.
- Theming via CSS variables, not React props or build-time swap.

## Quick links

- [`AGENT.md`](AGENT.md)
- [`SKILLS.md`](SKILLS.md)
- [`NEXT_STEPS.md`](NEXT_STEPS.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md)
