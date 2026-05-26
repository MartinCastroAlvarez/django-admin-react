# PM/UX acceptance — live status board

Owner: PM/UX role (`agents/product-manager/AGENT.md`).
Last reviewed: 2026-05-26.

Snapshot of every criterion in `ACCEPTANCE.md` §2 with its current
state. The Merger uses this table during the v0.1 release gate
review (`ACCEPTANCE.md` §5).

Legend: ✅ verified · 🟡 partially met · ⬜ blocked on dependency · ❌ regressed.

---

## §2.1 — Plug-and-play installation

| ID  | Criterion (short)                                                | Status | Blocked on                                  |
| --- | ---------------------------------------------------------------- | ------ | ------------------------------------------- |
| P-1 | ≤ 5 commands, ≤ 10 minutes from a clean Django 5 project          | 🟡     | Requires PyPI release; install-from-source path works today. |
| P-2 | Required config = INSTALLED_APPS + include() only                | ✅     | `conf.py` DEFAULTS verified, README accurate. |
| P-3 | No Node / pnpm needed on the consumer's machine                  | ⬜     | Depends on `scripts/build.sh` shipping the wheel with SPA bundle (Engineering). |
| P-4 | Package works at any URL mount                                   | 🟡     | `examples/project/` mounts at `/admin-react/`; package never hardcodes — but second-mount test not yet automated. |
| P-5 | Legacy admin keeps working alongside                             | ✅     | `examples/project/urls.py` runs both side-by-side; verified via screenshots. |

## §2.2 — Developer experience (Django dev, zero React)

| ID  | Criterion (short)                                                | Status | Blocked on                          |
| --- | ---------------------------------------------------------------- | ------ | ----------------------------------- |
| D-1 | Registering a `ModelAdmin` is sufficient                         | ✅     | API side fully proven by PR #4 — list + detail both delegate to `get_queryset` / `get_list_display` / `get_search_results` / `get_form` / `get_fields` / `get_exclude` / `get_readonly_fields`. SPA proof still PR #6 / #7. |
| D-2 | `ModelAdmin` edits propagate without frontend rebuild            | ⬜     | Requires the React SPA (PR #6 / #7). |
| D-3 | Consumer never edits `frontend/`                                 | ✅     | Verified — install path makes zero `frontend/` references. |
| D-4 | Errors surface with normal Django traceback                      | 🟡     | PR #4 catches `ValueError`/`TypeError` on bogus pk → 404, no stack-trace leak. SPA error boundary still PR #6. |
| D-5 | Every settings key documented in README                          | ✅     | README "Optional configuration" table = `conf.py` DEFAULTS. |

## §2.3 — Onboarding

| ID  | Criterion (short)                                                | Status | Blocked on                          |
| --- | ---------------------------------------------------------------- | ------ | ----------------------------------- |
| O-1 | First 400 words = what / who / install / get; no marketing       | ✅     | Verified post-PR #9 README rewrite. |
| O-2 | Screenshot grid in README (registry / list / detail / mobile / dark / login) | 🟡     | Five of six legacy-admin captures shipped; **dark-mode + real SPA captures** still depend on PR #6 / #7. |
| O-3 | ONBOARDING.md = five-minute path + three pitfalls                 | ✅     | Shipped in PM PR (PRODUCT_VISION + ONBOARDING). |
| O-4 | Anon → redirect to LOGIN_URL                                     | 🟡     | Backend redirect path verified via login screenshot; SPA-side check is PR #6. |
| O-5 | Non-staff → clear "need staff" message, not stack trace          | 🟡     | API returns JSON 403 via `permissions.py`; SPA's friendly empty state lands with PR #6. |

## §2.4 — Responsiveness

| ID  | Criterion (short)                                                | Status | Blocked on                          |
| --- | ---------------------------------------------------------------- | ------ | ----------------------------------- |
| R-1 | Usable at viewports ≥ 375 px                                     | ⬜     | Frontend (PR #6 / #7). |
| R-2 | Table → vertical card at < 640 px                                | ⬜     | Frontend. |
| R-3 | Forms stack vertically + labels associated at < 640 px           | ⬜     | Frontend. |
| R-4 | Touch targets ≥ 44 × 44 px                                       | ⬜     | Frontend. |
| R-5 | Nothing hover-only                                               | ⬜     | Frontend. |

## §2.5 — Accessibility (WCAG 2.1 AA)

| ID  | Criterion (short)                                                | Status | Blocked on                          |
| --- | ---------------------------------------------------------------- | ------ | ----------------------------------- |
| A-1 | Every interactive element has accessible name + focus ring       | ⬜     | Frontend. |
| A-2 | ≥ 4.5:1 normal text contrast in light + dark                     | ⬜     | Frontend. |
| A-3 | Full keyboard operation                                          | ⬜     | Frontend. |
| A-4 | Live-region announcements                                        | ⬜     | Frontend. |
| A-5 | Form errors via `aria-describedby` + text                        | ⬜     | Frontend. |
| A-6 | Respects `prefers-reduced-motion`                                | ⬜     | Frontend. |
| A-7 | Respects `prefers-color-scheme` on first paint                   | ⬜     | Frontend. |

## §2.6 — Documentation usability

| ID    | Criterion (short)                                              | Status | Blocked on                          |
| ----- | -------------------------------------------------------------- | ------ | ----------------------------------- |
| Doc-1 | README ≤ 350 lines                                             | ✅     | `wc -l README.md` < 350. |
| Doc-2 | Every code block in README + ONBOARDING runs as-is             | ✅     | Verified via `examples/project/`. |
| Doc-3 | API endpoints in `docs/api-contract.md` each have a happy-path example | ✅     | Verified. |
| Doc-4 | Every folder has a `README.md`                                 | ✅     | PM-owned + Architect-owned folders all have one. |
| Doc-5 | All cross-doc links resolve                                    | 🟡     | Last spot-check 2026-05-25; needs re-check pre-release. |

## §2.7 — SPA navigation

| ID  | Criterion (short)                                                | Status | Blocked on                          |
| --- | ---------------------------------------------------------------- | ------ | ----------------------------------- |
| N-1 | No full reloads between primary screens                          | ⬜     | Frontend. |
| N-2 | Back / forward / refresh preserve state                          | ⬜     | Frontend. |
| N-3 | URL = source of truth for shareable state                        | ⬜     | Frontend. |
| N-4 | Deep links survive permission loss                               | ⬜     | Frontend. |
| N-5 | Session expiry → Django login                                    | ⬜     | Frontend. |

## §2.8 — Visual consistency

| ID  | Criterion (short)                                                | Status | Blocked on                          |
| --- | ---------------------------------------------------------------- | ------ | ----------------------------------- |
| V-1 | One type scale / spacing / color tokens                          | 🟡     | `DESIGN_SYSTEM.md` specifies the system; implementation in PR #6. |
| V-2 | Closed button-variant set                                        | ⬜     | Frontend. |
| V-3 | Shared input states                                              | ⬜     | Frontend. |
| V-4 | Loading / empty / error / success use primitives                 | ⬜     | Frontend. |
| V-5 | Dark mode designed, not just inverted                            | ⬜     | Frontend. |

## §2.9 — Extensibility UX

| ID  | Criterion (short)                                                | Status | Blocked on                          |
| --- | ---------------------------------------------------------------- | ------ | ----------------------------------- |
| E-1 | `ModelAdmin` is the only extension surface                       | ✅     | API side: registry + list + detail all derive everything from the `ModelAdmin`. Full UX proof when SPA reads the per-model `permissions` block. |
| E-2 | Hiding Add button = `has_add_permission` → False                 | 🟡     | Backend exposes the boolean (PR #3 + PR #4 emit it in the `permissions` block); SPA hides on it (PR #6). |
| E-3 | Readonly fields render as text                                   | 🟡     | Detail endpoint now emits `readonly: true` per field (PR #4). Form rendering still PR #7. |
| E-4 | `list_display` mixing fields + callables works                   | 🟡     | List endpoint resolves callable list_display via `lookup_field` (PR #4). UI consumption still PR #7. |
| E-5 | Rebrand colors via single Tailwind config extension              | ⬜     | Frontend. |

---

## Summary

Snapshot 2026-05-26, post PR #4 review (`feat/backend-list-detail-endpoints`,
PM-approved, awaiting Architect + Security):

- **✅ Verified:** P-2, P-5, D-1, D-3, D-5, O-1, O-3, Doc-1, Doc-2, Doc-3,
  Doc-4, E-1 (12 criteria — net +2 since 2026-05-25).
- **🟡 Partially met:** P-1, P-4, D-4, O-2, O-4, O-5, Doc-5, V-1, E-2,
  E-3, E-4 (11 criteria — net +2 from ⬜, +0/-1 from ✅).
- **⬜ Blocked on frontend (PR #6 / #7):** the rest (~22 criteria) —
  every R-*, A-*, N-*, most V-*, D-2, E-5. Net -4 since 2026-05-25.

**v0.1 release gate (`ACCEPTANCE.md` §5):** still cannot pass until
the frontend lands, but PR #4 puts every backend-side §2 surface on
green. PM has shipped every doc, spec, and screenshot that is
buildable without the SPA.

Next PM action: track engineering PRs as they land, re-evaluate
each ⬜ on the day it should flip to ✅, and prepare the v0.1
CHANGELOG.
