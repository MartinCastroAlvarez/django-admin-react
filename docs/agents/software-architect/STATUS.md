# Software Architect — status

Live state of the Architect lane. Updated by every Architect session at
session start (sweep summary) and at session end (hand-off). Companion
to [`NEXT_STEPS.md`](NEXT_STEPS.md). For decisions see
[`DECISIONS.md`](DECISIONS.md).

Last updated: **2026-05-26** by `claude-architect-opus47-2026-05-26-2`.

---

## Sprint state — 2026-05-26

### Shipped (selected — full record on [the Project board](https://github.com/users/MartinCastroAlvarez/projects/3))

- **Backend feature wave** — autocomplete (#97), list_filter (#99),
  actions runner (#101), bulk PATCH + list_editable (#103),
  M2M r+w (#107), OpenAPI 3.1 schema (#108), inlines read-half
  (#109), files read-half (#110), frontend extension contract (#111).
- **Real-consumer pilot fixes** — SPA at non-root mount + login via
  AdminSite (#120), README screenshot grid removed (#121).
- **Dependency hygiene** — Dependabot advisories cleared in
  two waves (#122, #123).

### Open PRs the Architect lane has reviewed (2026-05-26 sweep)

| PR | Title | Architect verdict | Tier | Awaiting |
|---|---|---|---|---|
| [#79](https://github.com/MartinCastroAlvarez/django-admin-react/pull/79) | session-expiry contract | ✅ Approve (prior session + sweep) | 5 | Human merge |
| [#94](https://github.com/MartinCastroAlvarez/django-admin-react/pull/94) | api-contract `binary`/`range`/`json`/`register_field_type` clarifications | ⚠️ Request changes on §2 range shape (drift vs. code) | 5 | Author fixup |
| [#102](https://github.com/MartinCastroAlvarez/django-admin-react/pull/102) | v0.2 UX contracts (theming / PWA / mobile) | ✅ Approve pending cache-vs-`no-store` reconciliation in pwa.md §2.1 | 1 | Author fixup |
| [#104](https://github.com/MartinCastroAlvarez/django-admin-react/pull/104) | ACCEPTANCE.md §2 refresh against shipped v0.1 | ✅ Approve | 1 | Merger |
| [#105](https://github.com/MartinCastroAlvarez/django-admin-react/pull/105) | PM agent same-login `--comment-as-approval` + sweep cadence | ✅ Approve | 1 | Merger |
| [#112](https://github.com/MartinCastroAlvarez/django-admin-react/pull/112) | PM STATUS / NEXT_STEPS files | ✅ Approve | 1 | Merger |
| [#117](https://github.com/MartinCastroAlvarez/django-admin-react/pull/117) | Defense-in-depth: denylist on filters + FK-unregistered guard + RESERVED_APP_LABELS (closes #88 / #89 / #93) | ✅ Approve | 3 | Merger (PM/UX + Architect approves in) |
| [#118](https://github.com/MartinCastroAlvarez/django-admin-react/pull/118) | README screenshot removal | Superseded by #121 | 1 | Close |

### Issues the Architect lane carries

- **[#54](https://github.com/MartinCastroAlvarez/django-admin-react/issues/54)** Django inlines — read half shipped via #109; write half open. P0 / v0.1.
- **[#119](https://github.com/MartinCastroAlvarez/django-admin-react/issues/119)** Post-hoc Security audit — Architect concurs with **S-CRIT-1** (M2M silent-wipe in #107's `merged_initial_for_update`); follow-up PR owed. See [`NEXT_STEPS.md`](NEXT_STEPS.md) §1.

### Releases

- `0.1.0a1` cut as the first PyPI alpha.
- `0.1.0a2` cut at 15:10 UTC 2026-05-26 ([Discussion #98](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/98)). Includes #95 backend half of session-expiry, list_filter desc, actions descriptor, autocomplete.
- **`0.1.0` stable is blocked** — see [`NEXT_STEPS.md`](NEXT_STEPS.md) §3.

### v0.1.0 stable blockers (Architect-tracked)

1. **PR #117 merged** — defense-in-depth sensitive-name + unregistered-FK + reserved-segments guard.
2. **S-CRIT-1 follow-up merged** — M2M silent-wipe fix in `writes.py::merged_initial_for_update`.
3. **PR #94 merged or §2 reframed** — `range` wire shape resolved either by reframing to honest `str()` fallback or landing the structured serializer + tests.
4. **PR #79 + SPA modal PR merged** — session-expiry end-to-end.
5. **PR #102 merged + implementation PRs queued** — theming / PWA / mobile contracts before the screenshot capture work (#87) can run.
6. **Post-hoc audits on #97 / #99 / #101 / #103 / #107 / #108 / #109 / #110 / #111** — the 9 PRs Security flagged in #119.

### Risk register

- **Concurrent agents share the same working directory** — surfaced
  this session when reflog showed a parallel checkout. Mitigation:
  Architect sessions should use `git worktree add` to isolate, not
  share `cwd`. Captured in [`NEXT_STEPS.md`](NEXT_STEPS.md) §4.
- **PAT in `.git/config` remote URL** — surfaced this session. Repo
  owner's call to defer rotation; do not echo or commit the token.
- **Drift between `docs/api-contract.md` and code** — PR #94's
  `range` shape is the latest instance. The contract has to land
  with the implementation, not ahead of it.

---

## Required reading at session start

See [`AGENT.md`](AGENT.md) §"Required reading order". This file is
the live-state companion — the AGENT.md describes who the role is,
this file describes what's currently in flight.
