# PM/UX review — PR #32 `refactor(api): full audit cleanup — centralize helpers, expert-clean docs`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR: #32
Author: API/refactor role
Branch: `chore/api-audit-cleanup` (rebased on post-PR #31 `main`)

Per the 3-reviewer rule, this is the PM role-specific review.

---

## Scope I checked

`git diff main...origin/chore/api-audit-cleanup` reports **13 files,
+451 / -374** — all under `django_admin_react/api/` and `tests/`. No
URL changes, no settings changes, no template changes, no frontend
package touched.

Specifically:

- `django_admin_react/api/writes.py` — promotes four helpers to the
  public surface: `bad_request`, `validation_failed`,
  `not_found_response`, `load_object_or_none`. Adds module-level
  index of the public API.
- `django_admin_react/api/serializers.py` — renames `_label_for` →
  public `label_for(obj)` (the underscore-private form was being
  re-implemented in `views/list.py`). Docstring documents the
  `__str__`-raises fallback as a UX contract.
- `django_admin_react/api/views/{list,detail,create,update,destroy}.py`
  — each view drops its inlined `_NOT_FOUND_BODY` /
  `_not_found_response()` / `_label_for_obj()` duplicate and imports
  the centralized helper. JSON bodies and status codes unchanged.
- `tests/helpers.py` — new shared `admin_override` context manager,
  pulled out of five duplicated copies across
  `tests/test_{create,delete,detail,list,update}.py`.

`pytest -q` reports **142 passed** post-rebase — identical to the
post-PR #31 baseline. No tests added, none removed; same assertions,
same wire shape.

## Product / UX findings

### 1. Zero user-visible surface change (✅)
This is a pure refactor. Every JSON body, every status code, every
response header is byte-for-byte identical to what `main` ships
today. I spot-checked the 404 envelope (`{"error":{"code":
"not_found","message":"Not found."}}`), the FK envelope (`{"id":
pk, "label": str(obj)}`), and the `validation_failed` 400 shape —
all unchanged. The SPA, navigation flows, loading states, and any
downstream consumer of the wire contract see exactly nothing.

### 2. PR #31's `Cache-Control: no-store` fix is preserved (✅)
This was the load-bearing question for a rebase-onto-#31 PR. I
grepped `origin/chore/api-audit-cleanup` for `Cache-Control` and got
**10 hits** across `permissions.py`, `writes.py`, and every one of
the five view modules (`list`, `detail`, `create`, `update`,
`destroy`, `registry`). The centralized `not_found_response()`
sets `no-store` on every 404, the centralized `bad_request()` and
`validation_failed()` set it on every 400, and each 200 path
continues to set it inline. The PR #31 product-trust guarantee
survives the rebase intact. Security review on #32 confirms.

### 3. Onboarding / docs win (✅)
The new module-level docstring in `writes.py` lists every public
helper with a one-line purpose. `label_for`'s docstring explains
*why* the `<ClassName: pk>` fallback exists — half-migrated DB
state, missing related rows — which is exactly the kind of context
a future contributor needs and will not get from the code alone.
`tests/helpers.py::admin_override` documents the per-test admin
override pattern as **the canonical way to test "what does the
admin say?"**, which directly reinforces rule 1 of `CLAUDE.md` §2
(`ModelAdmin` is the only source of truth). That is product-doc
work done in code, and it lowers the onboarding tax for the next
agent or human contributor.

### 4. Single source of truth for 404 / label / queryset-load (✅)
Before this PR, three view modules each had a private copy of
`_NOT_FOUND_BODY` + `_not_found_response()`, and two modules each
had a private `_label_for` fallback. A future change to the 404
envelope (e.g., adding a `request_id` for support telemetry) would
have required edits in 3–5 places with high risk of drift. After
this PR, **one edit** in `writes.py` propagates everywhere. That is
real future-product-velocity, even though today's wire is
unchanged.

## Concerns

### Concern 1 (non-blocking): no new tests, but none needed
A pure refactor that leaves the test suite green at the same 142
count is the right outcome — the existing wire-contract tests are
the regression net. I confirmed that the `test_security.py`
`Cache-Control` assertions from PR #31 are among the 142 passing.
Not a blocker; just calling out that I checked.

### Concern 2 (non-blocking): public API surface widens slightly
Promoting four helpers from underscore-private to public means
they are now part of the package's de facto contract for any
downstream `ModelAdmin` extension code that imports from
`django_admin_react.api.writes`. We do not document an extension
API yet (the UX-extensibility contract thread is still open), so
this is fine for now — but when that contract lands, these helpers
should either be explicitly part of it or moved into an internal
module. Worth a follow-up note in `docs/agents/open-questions.md`.
I will file it myself if no one else does.

## Risks

- **Low for product.** No wire change, no copy change, no settings
  change. 142/142 tests pass.
- **No consumer install / migration impact.** Existing deployments
  pick up only internal Python-module reshuffles; the public
  install surface (URL include, `INSTALLED_APPS` entry) is
  untouched.
- **No frontend coordination needed.** `@dar/api` and downstream
  packages call URLs, not Python; they cannot observe this PR.
- **Rebase risk = neutralized.** The PR #31 `Cache-Control: no-store`
  hardening is intact across all read **and** write paths, now
  centralized rather than scattered (arguably stronger than #31's
  inline approach).

## Verdict

**Approve.**

This is a textbook small refactor: it removes duplication, lifts
private helpers to a documented public surface, centralizes the
404 / 400 / queryset-load contract, and raises the docstring bar
to "expert-clean" without changing a single byte of the wire. The
rebase preserved PR #31's `Cache-Control: no-store` fix on every
endpoint. Per `docs/agents/autonomy-policy.md`, this PR's
highest-touched tier is Tier 1 (`django_admin_react/api/` +
`tests/`), so the Merger can auto-merge after the Security and
Architect role reviews land.

— `claude-pm-ux-opus47`
