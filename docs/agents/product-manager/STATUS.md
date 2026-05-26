# PM/UX status

Last-updated: 2026-05-26
Last touched: ACCEPTANCE.md §2 refresh (PR #104), v0.2 UX contracts (PR #102), PM agent workflow notes (PR #105).
Active session id: `claude-pm-ux-opus47-2026-05-26`.

Update this file every session before quitting (per [`AGENT.md`](AGENT.md) §11).

---

## 1. Current sprint

**v0.1 P0 / P1 sprint** — closing the 12 issues filed by the user-agent
on 2026-05-26 ([Discussion #70](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/70))
through the v0.1.0a2 alpha release window. PM/UX role: triage every
issue, author UX contracts, refresh `ACCEPTANCE.md` against shipped
features, review every PR through the lane lens.

## 2. Where things stand (as of 2026-05-26 — late afternoon UTC)

### Releases

- `v0.1.0a1` shipped 2026-05-26 (PR #53).
- `v0.1.0a2` shipped 2026-05-26 (PR #96). The alpha designation is
  intentional — the release-gate mandate applies to v0.1.0 **stable**,
  which has not shipped.
- Stable v0.1.0 is **not yet ready** from the PM/UX lane — see §3
  below for the blockers.

### Backend (shipped during this sprint)

| Issue | Title                                              | Shipped via         |
| ----- | -------------------------------------------------- | ------------------- |
| #56   | `list_filter` taxonomy                             | PR #99              |
| #58   | `ModelAdmin.actions` + bulk-action endpoint        | PR #101             |
| #59   | `autocomplete_fields` / `raw_id_fields`            | PR #97              |
| #60   | Field-type vocabulary + `register_field_type` hook | PR #90              |
| #61   | `list_editable` + bulk PATCH                       | PR #103             |
| #62   | `date_hierarchy` drill-down                        | PR #80              |
| #63   | Session-expiry distinct error code (backend half)  | PR #95              |

### Open PRs (PM/UX-engaged)

| PR    | Lane     | Status                                                 |
| ----- | -------- | ------------------------------------------------------ |
| #79   | PM/UX    | Tier 5 — session-expiry SPA flow supplementing PR #95's §6.1. Awaiting reviewer re-read after realign + human merge. |
| #94   | PM/UX    | Tier 5 — vocab clarifications. Closes #92. Awaiting reviewer + human merge. |
| #100  | Architect| M2M read+write. PM/UX comment-approve posted; awaiting Security review. |
| #102  | PM/UX    | Tier 1 — `docs/ux/theming.md` + `pwa.md` + `responsive.md` §9. Refs #84/#85/#86. Awaiting one non-PM agent approve. |
| #104  | PM/UX    | Tier 1 — `ACCEPTANCE.md` §2 refresh (N-6/N-7/E-10/E-11/E-12). Awaiting one non-PM agent approve. |
| #105  | PM/UX    | Tier 1 — PM AGENT.md workflow notes (§9.5.1 / §9.5.2). Awaiting one non-PM agent approve. |

Open issue cards on the [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
remain triaged with priority / area / phase.

## 3. v0.1.0 stable blockers (from PM/UX lane)

Before PM/UX can sign off the v0.1.0 stable release under the
release-gate mandate, the SPA-FRONTEND implementation arc must
close. The BACKEND is largely done; the frontend is the critical
path. PM/UX has authored every UX contract these frontend PRs need
(see [`docs/ux/`](../../docs/ux/)).

Coarse-grained checklist:

- 🟡 SPA implementations consuming the merged backend contracts
  (#80 / #95 / #97 / #99 / #101 / #103 + #100 once it merges).
- 🟡 SPA implementations consuming the v0.2 UX contracts once PR
  #102 merges (dark mode + mobile patterns + PWA).
- 🟡 N-5 modal flow (pending PR #79 implementation slot).
- ⬜ Responsive audit (R-1..R-10).
- ⬜ Accessibility audit (A-1..A-7).
- ⬜ README screenshots (#87) — depends on the SPA being shippable.

## 4. Risk register

- **No frontend authors active** in observable sessions — the v0.2
  UX contract PRs (#102) and the existing SPA primitives may sit
  until a frontend lane session opens.
- **Same-login `--approve` blockage** — codified in PR #105 §9.5.1
  but not yet merged. Mergers need to know to read body verdicts.
- **PR #79 was once closed as "superseded"** by PR #95, then reopened
  after realign — small risk of a future reviewer re-closing without
  seeing the post-realign value-add. The reopen comment is explicit.

## 5. Hand-off pointers

- For the next PM/UX session: read this file → [`NEXT_STEPS.md`](NEXT_STEPS.md)
  → [`AGENT.md`](AGENT.md) §9.5.1 / §9.5.2 → sweep GitHub.
- For other roles consuming PM/UX output: every UX contract is in
  [`docs/ux/`](../../docs/ux/); every acceptance signal is in
  [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2 (after PR #104 merges).
