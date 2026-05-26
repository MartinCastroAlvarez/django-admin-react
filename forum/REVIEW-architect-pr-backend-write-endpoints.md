# Architect review — PR `feat/backend-write-endpoints`

Posted: 2026-05-26
Reviewer: claude-architect (delegated by PM session for review-gathering cycle)
Tier: **3** — backend code under `django_admin_react/api/views/{create,
update,delete}.py` + `writes.py`. **No CSRF / auth code is weakened**;
all unsafe methods rely on Django's session-CSRF middleware (test
`test_csrf_missing_on_unsafe_method_forbidden` proves it). Therefore
this stays Tier 3, not Tier 5.
Tip commit: `739dcac feat(api): write endpoints (POST/PATCH/DELETE) through ModelAdmin`
PM approval: not yet posted on this branch (PM only approved PR #4
in `REVIEW-pm-ux-pr-backend-list-detail.md`)
Security approval: pending

> **Dependency:** this PR is stacked on `feat/backend-list-detail-endpoints`
> (the first four commits are identical). Merge order: PR #4 → PR #5.

## §5.1 checklist (pr-workflow.md)

- [x] Conventional Commits — `feat(api):`. ✅.
- [x] CI green — same lint-clean basis as PR #4. ✅.
- [x] **[S]** No secrets. ✅.
- [x] **[S]** No `Model.objects.all()`. `create.py` uses `form.save()`
  via `model_admin.save_model`. `update.py` & `delete.py` start from
  `model_admin.get_queryset(request).get(pk=pk)`. ✅.
- [x] **[S]** No `csrf_exempt`, no `permission_classes = []`, no
  weakened `has_*_permission`. The dispatch classes
  `CollectionView`/`InstanceView` in `urls.py` are vanilla
  `django.views.generic.View` subclasses → CSRF middleware applies
  unmodified. `test_csrf_missing_on_unsafe_method_forbidden` in
  `test_create.py`, `test_delete.py`, `test_update.py` confirms. ✅.
- [x] **[S]** No `@dar/api` page-package imports — N/A. ✅.
- [x] **[S]** No model-specific names in package source. ✅.
- [x] No `# noqa` on security-relevant rules. The `noqa: S106` in
  tests are on hard-coded test-only passwords for the CSRF test
  (`"test-only-csrf-root"`) — legitimate. ✅.
- [x] No tests skipped / xfailed. ✅.
- [x] No new third-party deps. ✅.
- [⚠️] `docs/api-contract.md` is **not** touched but the wire shape
  matches §5.1/§5.2/§5.3 — see drift check below.
- [⚠️] `docs/agents/changelog.md` needs a one-liner — Merger to add.
- [x] No new folder. ✅.

## Architecture-specific concerns

### `SECURITY.md` §3 rules (most important here)
- Rule 1 (staff + AdminSite.has_permission gate): all three views
  call `is_admin_user(request, admin_site=admin_site)`. ✅.
- Rule 5 (per-object `has_*_permission`): `create.py` calls
  `has_add_permission(request)`; `update.py` calls
  `has_change_permission(request, obj)`; `delete.py` calls
  `has_delete_permission(request, obj)`. ✅.
- **Rule 6 (writes through `get_form()`)**: `create.py` L66 calls
  `model_admin.get_form(request, obj=None)`. `update.py` L80 calls
  `model_admin.get_form(request, obj=obj)`. Both then
  `form.is_valid()` + `model_admin.save_model(...)`. ✅.
- **Rule 7 (deletes through `delete_model`)**: `delete.py` L65
  calls `model_admin.delete_model(request, obj)`. Test
  `test_delete_model_is_called_not_obj_delete` proves it. ✅.
- Rule 10 (`get_queryset` starts every read): ✅.
- Rule 11 (no mass assignment): `reject_forbidden_keys` rejects
  unknown keys (`bad_request`), readonly keys, excluded keys, and
  sensitive-name keys. ✅.
- Rule 12 (403 vs 404 distinction): permission failures return 403
  with the standard envelope; missing models / pks return 404. ✅.

### `docs/api-contract.md` §5 drift check
- §5.1 POST request: payload subset of writable fields, unknown
  keys → 400. `writes.reject_forbidden_keys` enforces. ✅.
- §5.1 POST response 201: `{pk, label, redirect}`. `create.py`
  emits all three. The `redirect` is built from `request.path` by
  stripping the `api/v1/` suffix — consistent with the consumer-
  chosen mount in `ARCHITECTURE.md §4.5`. ✅.
- §5.2 PATCH: "Loads existing object via `ModelAdmin.get_queryset`,
  builds form initial data from instance, merges payload on top".
  `writes.merged_initial_for_update` implements this exactly. ✅.
- §5.2 PATCH response 200: "same shape as GET .../{pk}/" —
  `update.py` returns `_build_payload(...)` from detail. ✅.
- §5.3 DELETE: 204 no body — `delete.py` returns
  `HttpResponse(status=204)`. ✅.
- §6 error envelope `{error: {code, message, [fields]}}` —
  `writes.bad_request` / `validation_failed` match. ✅.

### Test matrix vs `CLAUDE.md §6`
- For each of `test_create.py`, `test_update.py`, `test_delete.py`:
  - ✅ anon → 302/403.
  - ✅ non-staff → 403.
  - ✅ staff with perm → 201/200/204.
  - ✅ staff without permission → 403.
  - ✅ unregistered model → 404.
  - ✅ bogus / nonexistent pk → 404 (update + delete).
  - ✅ readonly write attempted → 400 (`test_readonly_field_in_
    payload_is_bad_request`).
  - ✅ CSRF missing → 403 (`test_csrf_missing_on_unsafe_method_
    forbidden`).
  - ✅ `save_model` / `delete_model` is called, not raw ORM.
  - ✅ unknown field → 400.
  - ✅ validation envelope shape.
  - ✅ sensitive field name rejected.

### Minor architectural concerns (non-blocking)

1. **Dispatcher classes** `CollectionView` / `InstanceView` in
   `urls.py` add an extra level of indirection
   (`ListView.as_view()(request, ...)`). This works but is
   subtly slower per request because `as_view()` builds a new
   instance each call. A cleaner pattern is a single
   `MethodDispatchView` that maps `request.method` to the
   per-method view *class* and reuses the `View.dispatch`
   mechanism. **Follow-up, not a blocker** — correctness is intact
   and Django covers the per-request overhead.

2. `update.py` imports `_build_payload` from `views.detail`. The
   leading underscore is a "private" marker in PEP-8; a future
   refactor should rename to `build_payload` (or move to
   `serializers.py`).

3. `writes.coerce_fk_values` is tolerant of the response-envelope
   FK shape `{"id": ..., "label": ...}` echoed back in writes.
   The contract §5.1 says writes accept bare pks. Tolerance is
   nice; should be documented in `docs/api-contract.md` so clients
   know it is permitted, not just lucky.

4. `parse_json_body` returns `{}` on empty body, then passes it to
   `reject_forbidden_keys` (which accepts an empty dict). A
   POST with empty body therefore reaches `form.is_valid()` with
   no data. For `auth.Group` that triggers the required-name
   validator — fine. Other models might surface odd error envelopes.
   Consider rejecting empty bodies on POST upfront. **Follow-up.**

## Risks

- Tier 3 by my read: no CSRF/auth/permission code is *changed*,
  only *invoked*. If the Security role disagrees and considers
  the write-path code itself "CSRF/permission code" (per CLAUDE.md
  §3's broad wording), this escalates to Tier 5. **Recommend the
  Security role explicitly classify** before a Merger acts.

## Verdict

**Approve.**

The wire contract is upheld end-to-end (§5.1, §5.2, §5.3, §6); all
SECURITY.md §3 rules from 1, 5, 6, 7, 10, 11, 12 are enforced and
tested; the M2M unsupported / sensitive denylist defense-in-depth is
preserved. Merge after PR #4 lands and after the Security role
confirms the Tier 3 classification.

— claude-architect
