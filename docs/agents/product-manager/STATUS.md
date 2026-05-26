# PM/UX status

Last-updated: 2026-05-26 (late afternoon UTC)
Last touched: PR drive close-out + public-flip Discussion verdict ([#71](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71)) + S-CRIT-1 fix ([PR #130](https://github.com/MartinCastroAlvarez/django-admin-react/pull/130)) auto-closed Issue #119.
Active session id: `claude-pm-public-flip-2026-05-26`.

Update this file every session before quitting (per [`AGENT.md`](AGENT.md) §11).

---

## 1. Current focus

**Public-flip readiness review** — the repo-owner asked PM/UX to review whether the repo can flip from private to public, and to drive consensus on [Discussion #71](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71) with the other agent lanes. PM/UX verdict posted; consensus tracker on that thread.

Underneath that, the sprint window between `v0.1.0a2` (shipped) and the next alpha (`a3`, blocked on public-flip per [Discussion #98](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/98)) closed out cleanly: every open PR at the start of this session is merged or explicitly closed.

## 2. Where things stand (2026-05-26)

### Releases

- `v0.1.0a1` — shipped via [PR #53](https://github.com/MartinCastroAlvarez/django-admin-react/pull/53).
- `v0.1.0a2` — shipped via [PR #96](https://github.com/MartinCastroAlvarez/django-admin-react/pull/96). Known-cosmetic gap: PyPI page screenshots show as broken because the repo is still private; absolute `raw.githubusercontent.com` URLs 404. Fixed by public-flip + `0.1.0a3` re-introducing absolute URLs.
- `v0.1.0` (stable) — **not yet ready**. See §3 for the blockers.

### Backend features merged this sprint

| Issue | Title                                                       | Shipped via |
| ----- | ----------------------------------------------------------- | ----------- |
| #55   | M2M read+write                                              | PR #107     |
| #56   | `list_filter` taxonomy + apply on list endpoint             | PR #99      |
| #57   | `FileField`/`ImageField` read half (`{name, url, size}`)    | PR #110     |
| #58   | `ModelAdmin.actions` + bulk-action endpoint                 | PR #101     |
| #59   | `autocomplete_fields` / `raw_id_fields` (autocomplete endpoint) | PR #97  |
| #60   | Field-type vocabulary + `register_field_type` hook          | PR #90      |
| #61   | `list_editable` + bulk PATCH                                | PR #103     |
| #62   | `date_hierarchy` drill-down                                 | PR #80      |
| #63   | Session-expiry contract (backend + SPA UX)                  | PR #79 + #95 |
| #64   | OpenAPI 3.1 schema endpoint                                 | PR #108     |
| #65   | Frontend extension surface                                  | PR #111     |
| #119  | S-CRIT-1 M2M silent-wipe fix (writes.py)                    | PR #130     |
| #88   | Sensitive-name denylist on filter descriptors               | PR #117     |
| #89   | Unregistered-FK leak guard                                  | PR #117     |
| #93   | `RESERVED_APP_LABELS` reserved-segment guard                | PR #117     |

### Docs merged this sprint

`docs/api-contract.md` clarifications (#94), `docs/ux/{theming,pwa,responsive}.md` v0.2 UX contracts (#102 + #129 follow-up), `ACCEPTANCE.md` §2 refresh (#104), PM agent workflow notes (#105), PM agent priority order (#124), Security agent priority order (#126), Architect STATUS+NEXT_STEPS (#125), Architect decisions promotion (#128).

### Open PRs (PM/UX-engaged)

None as of session close. The PR queue is empty for the first time this sprint window.

### Open issues remaining

| Issue | Title                                                        | Phase | Priority | PM-side status |
|-------|--------------------------------------------------------------|-------|----------|----------------|
| #54   | Django inlines write-half                                    | v0.1  | P0       | Engineering owns; read half shipped via #109. |
| #84   | Dark mode                                                    | v0.2  | P1       | Contract merged via #102; frontend impl pending. |
| #85   | Mobile-first creative UX                                     | v0.2  | P1       | Contract merged via #102; frontend impl pending. |
| #86   | Android PWA                                                  | v0.2  | P2       | Contract merged via #102; frontend impl pending. |
| #87   | README + PyPI screenshots                                    | v0.1  | P1       | Blocked on #84/#85 frontend impl. |

## 3. v0.1.0 stable blockers (from PM/UX lane)

Before PM/UX can sign off the v0.1.0 stable release:

- 🟡 SPA implementations consuming the merged backend contracts (#80 / #95 / #97 / #99 / #101 / #103 / #107 / #108 / #109 / #110 / #111).
- 🟡 SPA implementations consuming the v0.2 UX contracts (dark mode + mobile patterns + PWA).
- 🟡 Inlines write half (#54).
- ⬜ Responsive audit (R-1..R-10).
- ⬜ Accessibility audit (A-1..A-7).
- ⬜ README screenshots (#87) — depends on the SPA being shippable.

Backend is largely done; frontend implementations are the critical path.

## 4. Risk register

- **No frontend authors active** in the observable session graph today — the v0.2 UX contracts and the existing SPA primitives may sit until a frontend lane session opens.
- **`0.1.0a3` is blocked on public-flip** — once the repo flips, the next release can ship with absolute screenshot URLs and fix the PyPI page rendering. Public-flip itself is a "human-required" change.
- **PR #112's STATUS.md was authored against a state that had since moved** — the lesson: STATUS.md should be authored *at session close*, not at session start, so it reflects merged reality not in-flight intent. This file follows that lesson.

## 5. Hand-off pointers

- Next PM/UX session: read this file → [`NEXT_STEPS.md`](NEXT_STEPS.md) → [`AGENT.md`](AGENT.md) §3.1 (work-priority order) + §9.5.1 / §9.5.2 → sweep GitHub.
- Security lane: post the Security-side verdict on [Discussion #71](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71) so the consensus tracker fills.
- Architect lane: post the Architect-side verdict on Discussion #71.
- Repo owner: review Discussion #71 once Sec + Arch verdicts land; final public-flip click is yours.
