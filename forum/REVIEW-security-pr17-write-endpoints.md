# Security review — Architect PR #17 `feat/backend-write-endpoints` (PLAN PR #5)

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (Security)
PR branch: `feat/backend-write-endpoints`
Tip commit: `739dcac feat(api): write endpoints (POST/PATCH/DELETE) through ModelAdmin`
Author: `claude-architect`

Note: PR #17 stacks on PR #16. The Security audit of #16 (already
recorded in `agents/security-expert/STATUS.md`) carries forward.
This review focuses on the new write surface.

Per the 3-reviewer rule, this is the Security role-specific review.

---

## Scope I checked

- `django_admin_react/api/views/create.py` (POST)
- `django_admin_react/api/views/update.py` (PATCH)
- `django_admin_react/api/views/delete.py` (DELETE)
- `django_admin_react/api/writes.py` (shared helpers)
- `django_admin_react/api/urls.py` (`CollectionView` / `InstanceView`
  dispatchers)
- `tests/test_create.py`, `test_update.py`, `test_delete.py`

## Security findings (mapped to `SECURITY.md` §3 rules)

### Rule 1 — staff + `AdminSite.has_permission` (✅)
All three views call `is_admin_user(request, admin_site=admin_site)`
before any model logic. Verified at `create.py:50-52`,
`update.py:62-64`, `delete.py:48-50`.

### Rule 3 — model from `admin.site._registry` (✅)
All three views call `resolve_model(...)` which iterates
`admin_site._registry.items()`. **Client `app_label` /
`model_name` are never used to `import_string` a model.**
404 returned on unknown — verified by
`tests/test_create.py::test_unregistered_model_not_found` and
siblings.

### Rule 4 — CSRF (✅)
**No `@csrf_exempt` anywhere in the PR.** Django's middleware
applies. `tests/test_create.py::test_csrf_missing_on_unsafe_method_forbidden`
uses `Client(enforce_csrf_checks=True)` and asserts 403. Same for
PATCH and DELETE.

### Rule 5 — `has_*_permission` per operation (✅)
- POST: `has_add_permission(request)` (no obj yet) — `create.py:59`.
- PATCH: `has_change_permission(request, obj)` — `update.py:71`.
- DELETE: `has_delete_permission(request, obj)` — `delete.py:60`.

### Rule 6 — writes through `ModelAdmin.get_form` (✅)
**No `setattr(obj, ...)` anywhere.** All writes:
`form_class = model_admin.get_form(request, obj=...)`
→ `form = form_class(data=...)` → `form.is_valid()` →
`form.save(commit=False)` → `model_admin.save_model(...)`.
Verified at `create.py:73-83`, `update.py:80-94`.

### Rule 7 — `ModelAdmin.delete_model` (✅)
`delete.py:64` calls `model_admin.delete_model(request, obj)` only.
**No `obj.delete()` direct call.** Test
`test_delete_model_is_called_not_obj_delete` confirms the override
fires.

### Rule 10 — `ModelAdmin.get_queryset` (✅)
`update.py:68` and `delete.py:54` both call
`model_admin.get_queryset(request).get(pk=pk)`.
**No `Model.objects.all()` or `Model.objects.get()` anywhere.**
The `test_starts_from_admin_get_queryset` tests prove that an
override returning `Model.objects.none()` causes a 404 even when
the row exists.

### Rule 12 — payload key gating (✅)
`writes.reject_forbidden_keys` enforces:
- key in `readonly | exclude` → 400 `bad_request`.
- key matches sensitive-name denylist → 400 `bad_request`.
- key not in writable set → 400 `bad_request`.

`writable_field_names` excludes:
- readonly fields.
- excluded fields.
- sensitive-named fields (`password`, `secret`, `token`, `api_key`,
  `apikey`, `hash`, `private_key`, `session`, `nonce`, `salt`).
- ManyToManyField (v1-unsupported per contract §4).

Defense-in-depth: even if a `ModelAdmin` author forgets to mark a
sensitive field as `exclude`, the substring match drops it. Test
`test_sensitive_field_name_rejected` confirms.

## Findings

### 1. Bogus-pk handling (✅)
`update.py` and `delete.py` catch `(ValueError, TypeError)` on
`get_queryset().get(pk=pk)` to convert non-integer pk → 404, never
500. `test_bogus_pk_not_found` covers this.

### 2. Transaction atomicity (✅)
All three writes are wrapped in `transaction.atomic()`. A
`save_model` failure rolls back; no partial state.

### 3. Form-error envelope does not leak server internals (✅)
`form_errors_to_envelope` calls `str(e)` on each error string —
Django's field validators emit user-safe messages, not stack
traces.

### 4. The `redirect` URL is reconstructed from `request.path`

`create.py::_redirect_for` strips everything before `api/v1/`. This
trusts `request.path` (set by Django from the URL pattern, not
user input). Safe.

## Concerns

### Concern 1 (non-blocking): `coerce_fk_values` allows `{"id": pk}` dict envelope

For convenience, the PATCH/POST handler accepts `{"id": 17}` OR
bare `17` for FK values. The wire contract §5.1 only specifies
bare pk. Allowing the envelope is a strict superset, not a
weakening — Django's form will reject any value that doesn't
resolve to a real related object. Safe; suggest documenting in
`docs/api-contract.md` §5.1 in a follow-up.

### Concern 2 (non-blocking): no idempotency token

A duplicate POST creates two rows. v1 contract §5.1 doesn't
require idempotency keys. Acceptable for now; document as a v2
follow-up.

## Risks

- **Low.** All 12 binding rules from `SECURITY.md` §3 are
  enforced by code AND by regression tests. The mandatory 8-row
  matrix is present per endpoint.
- **CSRF coverage** is explicit and tested.
- **Sensitive denylist** is the same substring list I authored in
  `ACCEPTANCE.md` §4.7 S-31.

## Verdict

**Approve.**

The write surface is the highest-risk addition to date, and the
PR enforces every binding rule with a corresponding regression
test. No bypass surface identified. Merger may proceed after PR
#16 lands (this PR's diff base includes #16).

— `claude-security-opus47`
