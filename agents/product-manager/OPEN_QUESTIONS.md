# PM/UX — OPEN QUESTIONS

Questions awaiting a decision from this role. When answered, move
the resolved summary to [`DECISIONS.md`](DECISIONS.md). Cross-role
questions live in [`../OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md).

## Format

```
## Q-<date>-<NN> — <topic>

Context: …
Options:
- A: …
- B: …
Tentative direction: …
```

---

## Q-2026-05-25-PM-01 — Should `docs/screenshots/` include "before / after vs HTML admin" pairs?

Context: Marketing value would be high (the visual contrast is the
sales pitch). Cost: every screenshot pair must be maintained when
the HTML admin changes, doubling the per-release maintenance.

Options:

- **A.** Ship "after" only (current SPA UI). Use a single hero shot
  in the README as the "modern admin" pitch.
- **B.** Ship "before / after" pairs in `docs/screenshots/compare/`,
  produced from the same example app.

Tentative direction: **A** for v1. Revisit at v1.x if the project
needs marketing collateral.

---

## Q-2026-05-25-PM-02 — Command palette (`cmd+k`) in v1 or v1.x?

Context: Linear / GitHub feel implies a command palette. It adds
significant scope (search index, keyboard plumbing, focus
management). The v1 scope is already large.

Options:

- **A.** Defer to v1.1. v1 ships keyboard nav (Tab, Esc, Enter) but
  no palette.
- **B.** Include a basic palette in v1 that only navigates between
  models (no search results inside models).

Tentative direction: **A**. The palette is a "polish" feature; v1
must first satisfy `ACCEPTANCE.md` §2.1-§2.5 cleanly.

---

## Q-2026-05-25-PM-03 — How do we surface custom `list_filter` in the SPA?

Context: Django Admin's `list_filter` shows a right-rail filter
sidebar. The SPA needs an equivalent. `PLAN.md` defers "complex
filters" but simple choice filters (`status = active/inactive`) are
common and valuable.

Options:

- **A.** v1 supports `list_filter` only when every entry is a
  `BooleanField`, `CharField` with `choices`, or an
  `IntegerField` with `choices`. Other entries are silently ignored
  in v1 (announced in docs).
- **B.** v1 supports nothing; all filters land in v1.1.

Tentative direction: **A**, conditional on the backend exposing a
small filter-options endpoint (handoff to Architect).

---

## Q-2026-05-25-PM-04 — Empty-state CTA on the registry page when the user has zero visible models

Context: A staff user with no permissions sees an empty registry.
The SPA should not display a blank screen.

Options:

- **A.** Show an `EmptyState` reading "You don't have access to any
  models. Ask an admin to grant view permissions." Link to Django
  admin documentation.
- **B.** Auto-redirect to `LOGIN_URL` (treat as not-logged-in).
- **C.** Show a generic "Welcome" card.

Tentative direction: **A**. Don't lie to the user.

---

> Append new questions above this line, newest on top.
