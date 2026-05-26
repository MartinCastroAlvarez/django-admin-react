# PM/UX next steps

Queue of the next things to do. Per [`AGENT.md`](AGENT.md) §11, move
completed items to [`DECISIONS.md`](DECISIONS.md) (with rationale) and
keep this list short.

Last-updated: 2026-05-26 (late afternoon UTC).

Apply [`AGENT.md`](AGENT.md) §3.1 work-priority order top-to-bottom.

---

## 1. Immediate — awaiting other lanes (no PM/UX action)

- [ ] [Discussion #71](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71) — Security lane verdict on public-flip readiness.
- [ ] [Discussion #71](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71) — Architect lane verdict on public-flip readiness.
- [ ] [Discussion #71](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71) — Repo-owner final go-button.

## 2. PM/UX hygiene to land before public-flip

Small Tier-1 PRs PM/UX committed to in the [Discussion #71 verdict](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71#discussioncomment-17065831). Land them in any order once the Sec + Arch verdicts come back:

- [ ] Pin a charter post in each of the four Discussion categories (Announcements / Q&A / Ideas / Show & Tell).
- [ ] `.github/ISSUE_TEMPLATE/` — bug + enhancement + security-via-advisory templates.
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` — role declaration + contract citation lines the autonomy policy expects.

## 3. PM/UX hygiene to land after public-flip

- [ ] Author the `0.1.0a3` release PR: restore absolute `raw.githubusercontent.com` URLs in `README.md` for the screenshot section (currently disabled because relative URLs render on PyPI but absolute URLs 404 on a private repo); cut the alpha and ship. Tier 6 (release), human-required.
- [ ] Open a Show & Tell Discussion with the consumer-pilot success story (from [Discussion #70](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/70) and [Discussion #116](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/116)) — anonymised further if needed by the owner.
- [ ] Iterate on the issue / PR templates after the first external contributor lands one.

## 4. Backlog — PM/UX-owned, blocked on frontend implementation

Each item below is PM/UX-acceptance-shaped but requires the SPA implementation PR consuming the merged backend / UX contract:

- [ ] N-5 modal flow (consuming PR #79's wire shape).
- [ ] N-7 list_filter sidebar + chip row (consuming PR #99 backend).
- [ ] N-8 date_hierarchy drill-down (consuming PR #80 backend).
- [ ] E-10..E-15 SPA-side implementations (consuming PRs #97 / #107 / #103 / #109 / #110 / #111).
- [ ] V-5 / V-6 / V-7 / V-8 dark mode (consuming PR #102 theming.md).
- [ ] R-6..R-10 mobile patterns (consuming PR #102 responsive.md §9).
- [ ] I-1..I-6 PWA installability (consuming PR #102 pwa.md as amended by PR #129).
- [ ] Issue #87 (screenshots) capture work — once V-5/V-6/V-7 + R-6..R-10 SPA implementations are sufficient.

## 5. Open architectural questions PM/UX is parked on

None. The 2026-05-26 sprint closed every PM/UX-side architectural question through PR review comments and issue triage. The five `open-questions.md` entries Architect promoted to decisions in [PR #128](https://github.com/MartinCastroAlvarez/django-admin-react/pull/128) included the PM × Architect cross-role question on `mount` derivation (resolved to **A** — request-derived — matching the PM/UX position).

## 6. Hand-off — to non-PM agents

- **Frontend lane (when active)**: the v0.2 UX contracts in `docs/ux/theming.md`, `pwa.md`, `responsive.md` §9 are the source of truth, plus `docs/ux/states.md` for the standard states. Issues #84/#85/#86 carry the tracking; the [Project board](https://github.com/users/MartinCastroAlvarez/projects/3) cards are at Todo, waiting for a claim.
- **Architect lane**: nothing PM-side outstanding. The Architect-side STATUS+NEXT_STEPS landed in [PR #125](https://github.com/MartinCastroAlvarez/django-admin-react/pull/125); cross-reference there.
- **Security lane**: PM/UX has no Security follow-ups outstanding. The Security agent's STATUS+NEXT_STEPS would land in a future PR mirroring the pattern in #125; cross-reference whenever it lands.

Whoever picks up frontend work should claim the Project board card first and post a claim comment on the driving issue.
