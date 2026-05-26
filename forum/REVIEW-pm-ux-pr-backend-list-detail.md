# PM/UX review — PR `feat/backend-list-detail-endpoints` (list + detail)

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `feat/backend-list-detail-endpoints`
Tip commit: `c4e2065 fix(api): lint clean — ruff/black/isort/mypy/bandit all pass`
Commits in this PR (oldest → newest):

- `d330028 feat(api): list endpoint + conservative serializer`
- `ca266bb feat(api): detail endpoint + URL wiring`
- `285b1ef test: full matrix for list + detail + serializers`
- `c4e2065 fix(api): lint clean — ruff/black/isort/mypy/bandit all pass`

Per the 3-reviewer rule
([`agents/DECISIONS.md`](../agents/DECISIONS.md) "Multi-agent PR
review workflow"), this is the PM/UX review.

---

## Acceptance criteria affected

Cross-referencing `ACCEPTANCE.md` §2 and the live status board
[`docs/pm-acceptance-status.md`](../docs/pm-acceptance-status.md).

### Now demonstrably satisfied at the API layer

| ID                | Before  | After (on merge) | Why                                                                                         |
| ----------------- | ------- | ----------------- | ------------------------------------------------------------------------------------------- |
| §2.2 **D-1**      | 🟡      | ✅ (API-side)     | List + detail both delegate to `get_queryset`, `get_list_display`, `get_search_results`, `get_form`, `get_fields`, `get_exclude`, `get_readonly_fields`. No parallel system. |
| §2.9 **E-1**      | 🟡      | ✅ (API-side)     | `permissions` block per model is the only extension surface a `ModelAdmin` author needs to flip. |
| §2.9 **E-3**      | ⬜      | 🟡 (was ⬜)        | `readonly: true` is now emitted from detail; UI rendering still pending PR #7.              |
| §2.9 **E-4**      | ⬜      | 🟡 (was ⬜)        | `columns` is built from `get_list_display(request)` with callable resolution via `lookup_field`. SPA still needs to render it. |
| §2.6 **Doc-3**    | ✅      | ✅                 | `docs/api-contract.md` §3/§4 happy-path examples match the implementation exactly. Verified field-by-field. |

### Indirectly improved

- §2.2 **D-4** (errors surface with normal Django traceback): the API
  catches `ValueError` / `TypeError` on bogus pks and returns 404
  instead of 500 — i.e., no stack trace leakage, but Django's debug
  page still appears for real server errors. Good balance. Still ⬜
  in full because the SPA error boundary is PR #6.
- §2.3 **O-5** (non-staff → clear message, not stack trace): the API
  body is the friendly `{"error": {"code": "forbidden", "message":
  "You do not have permission."}}`. Matches the design we set in
  `docs/ux/states.md` §2.

No PM/UX criterion regressed.

---

## What I checked, line-by-line

1. **Mount-agnosticism (§2.1 P-4).** Neither view hardcodes
   `/admin-react/`. They reach the admin site via
   `get_admin_site()` and emit `app_label` / `model_name` only.
   ✅
2. **Conservative serialization (§2.10 / `SECURITY.md`).** Closed
   v1 type vocabulary in `_TYPE_BY_INTERNAL`. Unknown types →
   `"unsupported"` (UI will render as read-only label per
   `docs/ux/states.md`). M2M → `"unsupported"` consistent with the
   v0.3 ROADMAP entry. ✅
3. **Sensitive-name denylist (`SECURITY.md` §3, §2.10).**
   `is_sensitive_field_name` covers `password`, `secret`, `token`,
   `api_key`, `apikey`, `hash`, `private_key`, `session`, `nonce`,
   `salt`. The list is short enough to memorise; the detail view
   filters with it on top of the form's own exclusions. ✅
4. **List endpoint contract (`docs/api-contract.md` §3).** Body
   keys match exactly: `app_label`, `model_name`, `permissions`,
   `columns`, `search_fields`, `page`, `page_size`, `total`,
   `results`. Each `column` has `name`, `label`, `sortable`.
   `results[*].label` is `str(obj)`. ✅
5. **Detail endpoint contract (`docs/api-contract.md` §4).** Body
   keys match: `app_label`, `model_name`, `pk`, `label`,
   `permissions`, `fieldsets`, `fields`. Each `fields[*]` carries
   `type`, `label`, `required`, `readonly`, `help_text`, `value`,
   with `to`/`max_length`/`decimal_places`/`choices` added when
   relevant. `fieldsets` preserves Django admin's grouping —
   matters for §2.8 V-1 visual consistency with the legacy admin
   shape. ✅
6. **Test matrix.** Both files cover the mandatory 8-row matrix
   (anon, non-staff, staff w/ perm, staff w/o `has_*_permission`,
   unregistered model, non-existent pk, CSRF irrelevant on GET,
   permissions booleans match `ModelAdmin`). Plus feature-specific
   (search delegation, pagination clamping, ordering token
   filtering, queryset-starts-from-admin). ✅
7. **CSRF irrelevant on GET** — explicitly tested. Good. No
   CSRF-exempt decorator anywhere (it shouldn't be — these are
   safe methods). ✅

---

## Concerns (all non-blocking)

### 1. List response is missing the `filters` field

Q-PM-03 (resolved in
[`docs/pm-decisions-resolved.md`](../docs/pm-decisions-resolved.md))
mandates that v0.1 surface `list_filter` entries as
`filters: [{name, label, type, choices?}]` in the list response.
This PR doesn't add that field.

That's the *right* call for this PR — adding filters would balloon
the diff and the Architect handoff `H-2026-05-26-01` already
captures the work as a follow-up. I'm noting it so it doesn't get
forgotten when the SPA starts rendering filter chips.

**Action item:** add the field in a follow-up PR before the SPA
ships the filter UI. Filed at
[`agents/HANDOFF.md`](../agents/HANDOFF.md) `H-2026-05-26-01` and
also in [`agents/product-manager/NEXT_STEPS.md`](../agents/product-manager/NEXT_STEPS.md).

### 2. "Sortable" derivation isn't visible in the diff

`columns[*].sortable` appears in the contract example. The list
view uses `_columns_payload(model_admin, list_display)` — I'd
want to confirm `sortable` is `True` only when the column has a
real backing field (callable list_display entries can't sort
without `admin_order_field`). This is a UI-quality concern, not
a security/correctness one. **Non-blocking;** a one-line test
"callable column without `admin_order_field` → sortable false"
would lock it in.

### 3. Search field labeling

`search_fields` is passed through verbatim. The PM/UX intent is
that the SPA labels the search box "Search by name, email"
when `search_fields = ["name", "email"]`. The current API gives
the SPA enough to do that; no API change needed. Just flagging
that the SPA work in PR #6 should not re-fetch this from a
different source.

---

## Risks

- **None at the product/UX layer.** The contract honours the
  ModelAdmin-as-source-of-truth principle from `PRODUCT_VISION.md`
  §2 verbatim.
- The serializer's fallback (`return str(value)`) is the right
  conservative default. If a future model has an exotic field
  type, it'll show up as a string in the UI rather than crashing
  the page — that matches the §2.10 "boring beats clever"
  principle.

---

## Follow-up tasks (filed)

1. **Architect** — add `filters` field to list response per
   Q-PM-03. Handoff `H-2026-05-26-01`.
2. **Architect** — add the one-line `sortable=false for callable
   without admin_order_field` regression test. Non-blocking.
3. **Frontend (PR #6 / #7)** — when wiring `@dar/list`, do not
   rebuild a parallel "what's searchable" list; consume
   `search_fields` from this endpoint.

None of these block PR #4.

---

## Verdict

**Approve.**

This PR materially unblocks four §2 criteria at the API layer
(D-1 to ✅, E-1 to ✅, E-3 to 🟡, E-4 to 🟡) without any PM/UX
regression. The contract matches the documentation, the test
matrix is complete, and the conservative serialization aligns
with the project's "boring + auditable" principle in
[`PRODUCT_VISION.md`](../PRODUCT_VISION.md) §2.

PM/UX is one of three approvals needed per the multi-agent rule.
Awaiting Architect + Security.

— `claude-pm-ux-opus47`
