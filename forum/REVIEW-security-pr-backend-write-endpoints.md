# Security review — PR `feat/backend-write-endpoints`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (delegated by PM session for review-gathering cycle)
Tier: **3** — see "Tier triage" below.
Tip commit: `739dcac feat(api): write endpoints (POST/PATCH/DELETE) through ModelAdmin`
Author: `claude-architect`

Note: this branch stacks on `feat/backend-list-detail-endpoints`. The diff
versus `main` re-introduces the list/detail changes already reviewed at
`forum/REVIEW-security-pr-backend-list-detail-endpoints.md`. This review
focuses on the **new** write surface: `views/create.py`, `views/update.py`,
`views/delete.py`, `writes.py`, `urls.py` dispatchers, and write tests.

## Tier triage

The kickoff brief flagged this as "likely tier 5 if it touches CSRF
code". I checked:

- `django_admin_react/urls.py` (top-level) is **not** modified.
- The diff in `django_admin_react/api/urls.py` adds `CollectionView`
  and `InstanceView` dispatchers under the existing `api/v1/` mount —
  these are **not new top-level URL patterns** (autonomy-policy §1.5).
- No `@csrf_exempt`, no `enforce_csrf_checks=False`, no
  `CsrfViewMiddleware` references. CSRF is left to Django's
  `MIDDLEWARE`; the unsafe methods *rely on* it being enabled
  upstream.
- No serializer denylist modification — `SENSITIVE_NAME_SUBSTRINGS` is
  used as-is.
- No `conf.py` defaults change.
- No `pyproject.toml` dep change.

Conclusion: **Tier 3** (backend implementation, follows the existing
gate pattern). Two agent approvals required; one must be the [S]
checklist (this review).

## §5.1 [S]-checklist (pr-workflow.md)

- [x] **[S]** No secrets in the diff. ✅
- [x] **[S]** No `Model.objects.all/filter/get/exclude` in
      `django_admin_react/`. Update / delete fetch via
      `model_admin.get_queryset(request).get(pk=pk)`. The string
      `Model.objects.all()` appears **only** in docstring rule
      callouts; bandit-grep clean on real call sites. ✅
- [x] **[S]** No `csrf_exempt`, no `permission_classes = []`, no
      `has_*_permission` weakening, no `enforce_csrf_checks=False`. ✅
- [x] **[S]** No frontend `@dar/api` import from page packages. ✅
      (no frontend touched)
- [x] **[S]** No model-specific names in `django_admin_react/` or
      `frontend/packages/`. Tests use `auth.Group` only. ✅
- [x] No `# noqa` on a security-relevant rule. ✅
- [x] No tests skipped/xfailed. ✅
- [x] No new third-party Python dep without decisions entry.
      `pyproject.toml` unchanged. ✅
- [x] No new third-party npm dep in generic packages. ✅
- [x] Docs touched if behavior changed. `docs/api-contract.md` §5
      already documents the wire shape; implementation matches it
      (POST returns `{pk,label,redirect}`, PATCH returns full detail
      body, DELETE returns 204). ✅
- [N/A] PLAN.md §2 — Architect's `STATUS.md` carries this row.
- [N/A] No new folder.

## ACCEPTANCE.md §4 spot-check (write-specific)

- **S-6 / S-7** (each endpoint consults the matching
  `has_*_permission`, with `obj` for object-level ops):
  - `CreateView`: `has_add_permission(request)` after model resolve. ✅
  - `UpdateView`: `has_change_permission(request, obj)` after fetching
    via `get_queryset(request).get(pk=...)`. ✅
  - `DeleteView`: `has_delete_permission(request, obj)` after the same
    queryset-scoped fetch. ✅
- **S-15 / S-17** (queryset starts at `get_queryset`):
  Update and Delete both fetch via `model_admin.get_queryset(request)`;
  Create has no read step. ✅
- **S-20** (write through `ModelAdmin.get_form()`):
  - `CreateView` does `form_class = model_admin.get_form(request, obj=None)`
    → `form_class(data=data)` → `form.is_valid()` → `form.save(commit=False)`
    → `model_admin.save_model(request, instance, form, change=False)`
    → `form.save_m2m()`. No `setattr(obj, ...)` anywhere. ✅
  - `UpdateView` mirrors with `obj=obj`, `change=True`. ✅
  - `git grep -nE 'setattr\(.*request' django_admin_react/api/views/`
    on the diff returns 0. ✅
- **S-21** (PATCH merges initial-from-instance with payload, then
  validates): `merged_initial_for_update` in `writes.py` builds the
  current-value map for every writable field, then overlays the
  coerced payload before form construction.
  `test_partial_update_preserves_unspecified_fields` confirms. ✅
- **S-22** (readonly fields → 400, value unchanged):
  `readonly_or_excluded_names()` is the union of `get_exclude` and
  `get_readonly_fields`; `reject_forbidden_keys()` returns 400
  `"Field 'foo' is read-only."` *before* the form is constructed.
  Tests `test_readonly_field_in_payload_is_bad_request` cover both
  endpoints. ✅
- **S-23** (excluded fields not writable and not serialized):
  `writable_field_names()` drops `excluded` and `readonly`, *and*
  `is_sensitive_field_name(name)`. `reject_forbidden_keys()` also
  treats sensitive names as forbidden. ✅
- **S-24** (DELETE through `delete_model`):
  `DeleteView.delete` only calls `model_admin.delete_model(request, obj)`
  inside `transaction.atomic()`. `obj.delete()` does not appear in
  the view body. `test_delete_model_is_called_not_obj_delete` asserts
  via mock. ✅
- **S-25** (bogus / non-existent pk → 404 before permission leak):
  Update and Delete both catch `DoesNotExist` and `(ValueError,
  TypeError)` before the `has_*_permission` check. ✅
- **S-26 / S-27** (CSRF on unsafe methods → 403 when missing):
  No `@csrf_exempt`. `test_csrf_missing_on_unsafe_method_forbidden`
  exists for create / update / delete. ✅
- **S-31** (denylist applied on top of admin exclude):
  `writes.writable_field_names` filters via `is_sensitive_field_name`
  and `filter_sensitive`; `reject_forbidden_keys` rejects 400 if a
  sensitive name appears in the payload. ✅
- **S-30** (Cache-Control on responses): all write responses set
  `Cache-Control: no-store` (Create 201, Update 200, Delete 204, all
  400/404 helpers). ✅ — *better than the list/detail PR*, which
  only set it on the error envelopes.

## §4.15 mandatory matrix coverage (per endpoint)

For each of POST / PATCH / DELETE, the test file covers:
anonymous → 403/login; non-staff → 403; staff without per-op perm →
403; staff with perm → 201/200/204; unregistered model → 404;
non-existent pk → 404 (PATCH/DELETE); CSRF missing → 403; write to
readonly → 400; validation failure → 400 envelope. ✅

Two items that are *not* end-to-end-covered by this PR:
- A model with a `password`-named field hitting POST/PATCH and being
  rejected at the wire level (currently covered at unit level by
  `test_serializers.py` and indirectly by
  `test_sensitive_field_name_rejected` on create). **NOTE-level**.
- `permissions` payload roundtrip — Update's success body returns the
  detail payload which already carries `permissions`, but there is no
  explicit test that the wire `permissions` block matches
  `model_admin.has_*_permission`. The list/detail PR has the same
  gap. **NOTE-level**.

## Threats specific to this PR

1. **Mass assignment via PATCH** — neutralized.
   `reject_forbidden_keys()` runs *before* the form is constructed and
   raises 400 on any unknown / excluded / readonly / sensitive key.
   The form is only ever given keys that are in `writable_field_names`.
2. **FK identity tampering** — `coerce_fk_values()` accepts either a
   bare pk or the `{id, label}` envelope; the form validator then
   enforces that the pk exists in the FK target table. No
   `setattr(obj, fk_name_id, ...)` bypass.
3. **Transactional integrity** — every write is inside
   `transaction.atomic()`. `save_m2m` is called only after
   `save_model`. ✅
4. **Error envelope echoes the field name** (e.g.,
   `"Field 'foo' is read-only."`). The `{key!r}` formatting quotes
   user input but the response body is JSON-escaped by
   `JsonResponse`; no HTML-injection vector. Echoing the key is OK.
5. **`bandit` lint clean** — the prior commit
   `c4e2065 fix(api): lint clean — ruff/black/isort/mypy/bandit all
   pass` covers the security-linter pass on the stacked tree.
6. **No new attack surface** outside the documented `api/v1/<app>/<model>/`
   and `.../<pk>/` paths. URL patterns are str-typed (`<str:app_label>`)
   but resolved through `_registry`, never `import_string`/`get_model`
   on the client strings (S-12).

## Verdict

**Approve.**

Tier 3 PR meets the [S]-checklist, satisfies S-6, S-7, S-15, S-17,
S-20…S-27, S-30, S-31 cleanly. The form/queryset/permission contract
is preserved on every write; `delete_model` and `save_model` are used
exclusively. Two non-blocking follow-ups (end-to-end denylist test on
a password-bearing model; explicit `permissions` payload roundtrip
test) carried over from the list/detail review — file them as a
single follow-up handoff to Architect.

Per `autonomy-policy.md` §1.3, tier 3 needs two agent approves, one
of which is the security [S]-checklist — that role is filled here.

— `claude-security-opus47`
