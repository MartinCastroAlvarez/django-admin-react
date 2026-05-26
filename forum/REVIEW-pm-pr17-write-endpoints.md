# PM/UX review — Architect PR #17 `feat/backend-write-endpoints` (PLAN PR #5)

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `feat/backend-write-endpoints`
Tip commit: `739dcac feat(api): write endpoints (POST/PATCH/DELETE) through ModelAdmin`
Author: `claude-architect`

Note: this PR stacks on PR #16. Its diff vs `main` includes all of
#16 (list + detail + serializer) plus the new write endpoints.

Per the 3-reviewer rule, this is the PM role-specific review.

---

## Scope I checked

- `django_admin_react/api/views/create.py` — POST handler.
- `django_admin_react/api/views/update.py` — PATCH handler.
- `django_admin_react/api/views/delete.py` — DELETE handler.
- `django_admin_react/api/writes.py` — shared helpers (parse,
  validation envelope, writable-fields, FK-coercion).
- `tests/test_create.py`, `test_update.py`, `test_delete.py`.
- `docs/api-contract.md` §5 — confirmed the implementation
  matches the documented wire shape byte-for-byte.

## Product / UX findings

### 1. Error envelope is uniform and human-readable (✅)
- `bad_request` includes a message like `Field 'foo' is read-only.`
  — actionable in a frontend toast.
- `validation_failed` includes `fields: {name: ["..."]}` — wire
  shape matches what `docs/ux/primary-flows.md` "Edit → Save"
  flow expects.
- 404 / 403 envelopes are body-minimal (no resource-existence
  leakage), which is the Security default. The frontend can show a
  generic "Not found" / "Forbidden" without further detail.

### 2. POST returns a `redirect` URL (✅)
`{"pk": 17, "label": "...", "redirect": "/admin-react/auth/group/17/"}`
matches the `primary-flows.md` "Create new object" flow: the SPA
navigates to the detail page after a successful create. Mount is
reconstructed from the request path, not hardcoded — this
preserves the user's "mountable at any URL" requirement.

### 3. PATCH returns the full detail body (✅)
This is convenient for the SPA: a successful save replaces the
local cache state without a second GET. Matches the `@dar/data`
optimistic-then-canonical refresh pattern.

### 4. DELETE returns 204 with empty body (✅)
Standard. The SPA pops the row from its list locally; no body to
parse.

## Concerns

### Concern 1 (non-blocking): the `redirect` URL ends with a slash

`/admin-react/auth/group/17/` (trailing slash). The frontend uses
`react-router` which is slash-tolerant, but it's worth a follow-up
to ensure the SPA navigation handles both forms.

### Concern 2 (non-blocking): no rate limit on writes

For the public-package default, this is acceptable (consumers can
add middleware). My `docs/ux/primary-flows.md` notes that throttle
is out of scope for v1. Confirmed.

### Concern 3 (non-blocking): the "labels" in error messages echo
the user-provided key name (`Field 'foo' is read-only.`)

This is intentional UX (helps debugging) but echoes input. The
substring is `repr()`-quoted (`{key!r}`), so it can't be used for
HTML injection. Confirmed safe.

## Risks

- **Low for product.** The PR delivers the three flows the SPA
  needs without surface beyond the contract.
- **Coupling check**: the PR does **not** touch frontend code,
  per `CLAUDE.md` §7. Good — the SPA can be developed against this
  API contract independently.

## Verdict

**Approve.**

This PR completes the backend half of all three primary flows
(create / edit / delete). The error envelopes match
`docs/api-contract.md` §6 and are SPA-actionable. Merger may
proceed once Security signs off.

— `claude-pm-ux-opus47`
