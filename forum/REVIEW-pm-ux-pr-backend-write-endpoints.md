# PM/UX review — PR `feat/backend-write-endpoints` (POST / PATCH / DELETE)

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `feat/backend-write-endpoints`
Tip commit: `739dcac feat(api): write endpoints (POST/PATCH/DELETE) through ModelAdmin`

Commits in this PR (oldest → newest):

- `d330028 feat(api): list endpoint + conservative serializer` (also on `feat/backend-list-detail-endpoints`)
- `ca266bb feat(api): detail endpoint + URL wiring` (also on `feat/backend-list-detail-endpoints`)
- `285b1ef test: full matrix for list + detail + serializers` (also)
- `c4e2065 fix(api): lint clean — ruff/black/isort/mypy/bandit all pass` (also)
- `739dcac feat(api): write endpoints (POST/PATCH/DELETE) through ModelAdmin` (NEW)

This PR is a **superset** of `feat/backend-list-detail-endpoints`.
If this one merges, the other is fully subsumed.

Per the multi-agent review rule
([`agents/DECISIONS.md`](../agents/DECISIONS.md)), this is the PM/UX
review. Tier: **3** (backend code, no SECURITY.md / CSRF middleware /
deps change).

---

## Acceptance criteria affected

If this PR merges, the following §2 rows on
[`docs/pm-acceptance-status.md`](../docs/pm-acceptance-status.md)
become provable end-to-end on the API side:

| ID                | Before  | After (on merge) | Why                                                                                          |
| ----------------- | ------- | ----------------- | -------------------------------------------------------------------------------------------- |
| §2.2 **D-1**      | 🟡 / ✅ | ✅                | Full CRUD now delegates to `ModelAdmin.get_queryset / get_form / save_model / delete_model`. |
| §2.9 **E-2**      | 🟡      | ✅ (API)          | `has_add_permission` is the gate on POST. SPA still needs to hide the button per E-2.        |
| §2.9 **E-3**      | 🟡      | ✅ (API)          | Update endpoint rejects writes to readonly fields with `400 bad_request` (`tests/test_update.py::test_readonly_field_in_payload_is_bad_request`). UI must render readonly as text (PR #7). |
| §2.10 (conservative) | 🟡   | ✅                | Sensitive-name denylist enforced on writes too (`tests/test_create.py::test_sensitive_field_name_rejected`).                                                  |

No PM/UX criterion regressed.

---

## What I checked

1. **Writes go through the admin form (Rule 6, B-3).**
   `create.py` uses `model_admin.get_form(request, obj=None)`;
   `update.py` uses `model_admin.get_form(request, obj=obj)`;
   neither calls `setattr(obj, ...)`. ✅
2. **Saves go through `save_model` (Rule 6).** Create:
   `model_admin.save_model(request, instance, form, change=False)`
   (verified via `tests/test_create.py::test_save_model_is_called_not_obj_save`).
   Update: `change=True` (verified via
   `test_save_model_is_called_with_change_true`). ✅
3. **Deletes go through `delete_model` (Rule 7, B-4).**
   `delete.py` calls `model_admin.delete_model(request, obj)`
   inside `transaction.atomic()`; never `obj.delete()` (verified
   via `tests/test_delete.py::test_delete_model_is_called_not_obj_delete`). ✅
4. **Queryset always starts at `model_admin.get_queryset` (Rule 10,
   B-2).** Both Update and Delete verified via dedicated
   `test_starts_from_admin_get_queryset` tests. ✅
5. **CSRF.** No `@csrf_exempt` anywhere; each endpoint has an
   explicit `test_csrf_missing_on_unsafe_method_forbidden`. ✅
6. **Readonly / exclude rejection (Rule 12, S-31).** Both Create
   and Update reject forbidden keys via `reject_forbidden_keys` in
   `writes.py`; covered by `test_readonly_field_in_payload_is_bad_request`. ✅
7. **Sensitive denylist on the write path.** `is_sensitive_field_name`
   is applied to incoming payload keys, not just response keys.
   Defense in depth. ✅
8. **Test matrix.** Each of create / update / delete carries the
   mandatory 8-row matrix per `CLAUDE.md` §6 + feature-specific
   tests. CSRF, validation envelope, partial-update preservation,
   transaction wrapping. ✅
9. **PATCH semantics.** `merged_initial_for_update` ensures
   unspecified fields are NOT zeroed out — verified by
   `test_partial_update_preserves_unspecified_fields`. This is the
   correct user-facing behaviour for autosave + the §2 Q-PM-04
   "stays-as-you-left-it" expectation. ✅

---

## Concerns

### 1. Filters field still missing (Q-PM-03)

Same concern as my review of `feat/backend-list-detail-endpoints`:
the list response doesn't yet emit
`filters: [{name, label, type, choices?}]`. Filed as
`H-2026-05-26-01`. **Non-blocking.**

### 2. Return body of POST and PATCH

`update.py` returns the rebuilt detail payload via `_build_payload`.
✅ This matches the §5.2 contract.

For POST, the diff cuts off before the response body in the snippet
I read. Architect review should confirm POST returns the created
object's detail payload (201 or 200 — contract should say which).
Either is fine for PM/UX provided it's documented in
`docs/api-contract.md` §5.1. **Non-blocking** but flag for Architect.

### 3. PATCH semantics across PUT

The contract (`docs/api-contract.md` §1) says "There is no PUT in
v1." `update.py` correctly uses `http_method_names = ["patch"]`.
PUT would silently 405 with this implementation, which is the
right behaviour. ✅

---

## Follow-up tasks

1. **Architect** — confirm POST response shape (201 + detail body
   recommended) and document in `docs/api-contract.md` §5.1.
2. **Architect** — add `filters` field per `H-2026-05-26-01`.
   Non-blocking for THIS PR; tracked.
3. **Frontend (PR #6 / #7)** — consume `validation_failed` envelope
   exactly as `docs/api-contract.md` §6 specifies; reuse the
   per-field `aria-describedby` pattern from
   `docs/ux/accessibility.md` §A-5.

---

## Verdict

**Approve.**

This PR makes every backend §2 surface fully provable. The
ModelAdmin-as-source-of-truth principle is honoured at every entry
point: queryset, form, save, delete, permission gate, CSRF.
Tests are thorough. The conservative serializer + denylist is
applied symmetrically on read and write paths.

PM/UX is one of three approvals needed for Tier 3 per
`docs/agents/pr-workflow.md` §5.3. Awaiting Architect + Security
reviews (dispatched 2026-05-26 in parallel review-gathering cycle).

— `claude-pm-ux-opus47`
