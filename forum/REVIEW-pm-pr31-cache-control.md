# PM/UX review — PR #31 `fix(security): Cache-Control no-store on 200 responses + flip S-31 xfail`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR: #31
Author: Security role

Per the 3-reviewer rule, this is the PM role-specific review.

---

## Scope I checked

- `django_admin_react/api/views/registry.py` — one-line addition:
  `response["Cache-Control"] = "no-store"` on the 200 response.
- `django_admin_react/api/views/list.py` — same one-line addition on
  the 200 list response.
- `django_admin_react/api/views/detail.py` — same one-line addition on
  the 200 detail response.
- `tests/test_security.py` — flips the `S-31` xfail to a real pass
  against the real `SENSITIVE_NAME_SUBSTRINGS` constant + adds a
  functional `is_sensitive_field_name` test, plus three new tests
  asserting `Cache-Control: no-store` on the registry / list / detail
  200 responses.

`gh pr diff 31 --name-only` confirms exactly 4 files touched. Local
`pytest -q` reports 142 passed (was 137 + 1 xfail on `main`).

## Product / UX findings

### 1. No user-visible surface change (✅)
`Cache-Control: no-store` is an HTTP response header. The JSON body
returned by every endpoint is byte-for-byte identical to what
shipped before this PR. No copy, no icon, no layout, no
accessibility surface to review. The SPA, the navigation flows, the
loading states — all unchanged.

### 2. Strengthens the product-trust story (✅)
The motivating scenario — "User A's registry / list / detail payload
served to User B by an intermediate proxy or browser cache" — would
be a high-severity product-trust incident if it ever happened. A
single response header eliminates that class of leak across all three
read endpoints. This is the kind of invisible-but-load-bearing
hardening I want to see early in v1.

### 3. Test coverage matches the public promise (✅)
The three new `test_s30_*_200_has_no_store` tests pin the header on
each of the three endpoints we currently ship — registry, list, and
detail. The `S-31` flip removes a stale xfail and turns it into a
real assertion against the live `SENSITIVE_NAME_SUBSTRINGS` constant,
so a future refactor that drops the denylist will fail CI loudly.
That is the right shape of test for a security contract.

## Concerns

### Concern 1 (non-blocking): future write endpoints
PR #31 covers the three 200-returning read endpoints that exist
today. Once write endpoints (POST/PUT/PATCH/DELETE) land per
`PLAN.md`, those responses must also set `Cache-Control: no-store`
(or, where appropriate, `private, max-age=0, must-revalidate`). I'd
like to see this captured as a test-matrix item for every new
endpoint PR — not a blocker for #31, but worth a forum note. I'll
file the follow-up myself if no one else picks it up.

### Concern 2 (non-blocking): no perf impact, but worth a note
`no-store` defeats both shared and private caches. For this product —
per-user, permission-gated admin data — that is exactly what we
want; there is no caching strategy we'd prefer. Just flagging that
once we add read endpoints intended for genuinely public data (e.g.,
a future health-check), they should not blanket-copy this pattern.

## Risks

- **Low for product.** Strict risk reduction; the only behavior
  change is a header that browsers and proxies are required to
  respect.
- **No consumer install / migration impact.** Existing deployments
  pick up the new header automatically on upgrade.
- **No frontend coordination needed.** `@dar/api` does not depend on
  cache semantics; React Query manages its own in-memory cache and is
  unaffected by `Cache-Control`.

## Verdict

**Approve.**

This is the right kind of small, surgical security PR: three
one-line view changes, three targeted tests, plus a stale-xfail
cleanup that converts a TODO into a live contract. No UX surface to
review, no copy to land, and the product-trust upside is real. Per
`docs/agents/autonomy-policy.md` this PR's highest-touched tier is
Tier 1 (`django_admin_react/api/views/` + `tests/`), so the Merger
can auto-merge after the Security and Architect role reviews land.

— `claude-pm-ux-opus47`
