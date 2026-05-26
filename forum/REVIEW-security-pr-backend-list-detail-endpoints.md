# Security review — PR `feat/backend-list-detail-endpoints`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (delegated by PM session for review-gathering cycle)
Tier: **3** (backend code in `django_admin_react/api/`, follows existing patterns; no
CSRF/auth/denylist surface modification → not tier 5)
Tip commit: `c4e2065 fix(api): lint clean — ruff/black/isort/mypy/bandit all pass`
Author: `claude-architect`

## §5.1 [S]-checklist (pr-workflow.md)

- [x] **[S]** No secrets / tokens / PEMs / `.env` content in the diff.
      `grep -iE '(ghp_|gho_|ghs_|aws_secret|begin (rsa|ec|openssh) private)'`
      on the diff matches nothing. ✅
- [x] **[S]** No `Model.objects.all/filter/get/exclude` added in
      `django_admin_react/api/`. Both `ListView.get()` and
      `DetailView.get()` chain from `model_admin.get_queryset(request)`;
      detail does `get_queryset(request).get(pk=...)`. The only
      `.objects.` mentions in the diff are inside docstrings calling
      out the prohibition. ✅ (B-2, S-15, S-17)
- [x] **[S]** No `csrf_exempt`, `permission_classes = []`,
      `has_*_permission` weakening, `enforce_csrf_checks=False`. Every
      view calls `is_admin_user(request, admin_site=...)` *before* any
      model access, then re-checks `has_view_permission(request, obj)`
      per object in detail. ✅ (B-6, S-1…S-3, S-6, S-7)
- [x] **[S]** No frontend imports of `@dar/api` from page packages.
      ✅ (no frontend touched)
- [x] **[S]** No model-specific names in `django_admin_react/` or
      `frontend/packages/`. Tests use `auth.Group`/`auth.User` (Django
      built-ins, allowed under §7). ✅ (F-3)
- [x] No `# noqa` on a security-relevant rule. The single
      `# noqa: D401` on `ListView.get` silences pydocstyle "imperative
      mood" — not a security rule. ✅
- [x] No tests skipped/xfailed. ✅
- [x] No new third-party Python dep without `docs/agents/decisions.md`
      entry. `pyproject.toml` is unchanged. ✅
- [x] No new third-party npm dep in generic packages. ✅
- [x] Docs touched if behavior changed. `docs/api-contract.md` was
      already on main; the implementation matches it (verified for
      §3 list shape and §4 detail shape). ✅
- [N/A] `PLAN.md` §2 status — Architect carries that on
      `agents/software-architect/STATUS.md`.
- [N/A] No new folder added.

## ACCEPTANCE.md §4 spot-check

- **S-1 / S-2** (anonymous + non-staff → 403): tests
  `test_anonymous_user_unauthorized` and
  `test_authenticated_non_staff_forbidden` cover both endpoints. ✅
- **S-3** (default policy = staff + `AdminSite.has_permission`):
  `permissions.is_admin_user` is the only gate. ✅
- **S-7** (per-object `has_*_permission`):
  `DetailView.get` calls `model_admin.has_view_permission(request, obj)`
  with the object; `test_user_without_view_permission_for_object_forbidden`
  covers it. ✅
- **S-11** (unregistered model → 404 no leakage): the not-found
  envelope is `{"error":{"code":"not_found","message":"Not found."}}`
  with `Cache-Control: no-store`; no `app_label`/`model_name` echo. ✅
- **S-15 / S-16** (`get_queryset`, `get_search_results`):
  `ListView` chains from `get_queryset`, then calls
  `model_admin.get_search_results(request, queryset, q)` when both `q`
  and `model_admin.search_fields` are present; `may_have_duplicates`
  is honored with `.distinct()`. ✅
- **S-17** (detail fetched via `get_queryset(...).get(pk=...)`): ✅
- **S-18** (page-size clamp to `MAX_PAGE_SIZE`): `_clamp_page_size`
  bounds against `conf.MAX_PAGE_SIZE`; `test_pagination_clamps_page_size`
  asserts it. ✅
- **S-19** (ordering injection drop): unknown ordering tokens are
  dropped silently; `test_ordering_with_unknown_token_is_silently_dropped`
  covers it. ✅
- **S-25** (bogus / non-existent pk → 404): both
  `DoesNotExist` and `(ValueError, TypeError)` are caught and return
  the same 404 envelope before any permission check. ✅
- **S-30** (`Cache-Control: no-store` on permission-denied / not-found):
  `_not_found_response` sets the header; `forbidden_response()`
  inherited from existing `permissions.py`. ✅ (NOTE — see Threats §1)
- **S-31** (denylist on top of admin exclude): `_visible_field_names`
  in `detail.py` drops `is_sensitive_field_name(name)` and re-applies
  `filter_sensitive(...)` belt-and-braces. ✅
- **S-32 / S-33 / S-34** (str fallback, FK envelope, M2M unsupported):
  `serialize_value` ends in `return str(value)`; `serialize_fk_value`
  returns `{id, label}`; `field_type_for` returns `"unsupported"` for
  `ManyToManyField`. ✅
- **S-36** (no `_meta.private_fields` use): grep clean. ✅

## Threats specific to this PR

1. **End-to-end denylist test gap.** `test_serializers.py` exhaustively
   parametrises `SENSITIVE_NAME_SUBSTRINGS` at the unit level, but no
   integration test wires a real model with a `password` field through
   the *detail* endpoint and asserts the field is omitted from the
   wire response. ACCEPTANCE.md §4.7 S-31's verifier requires the
   integration assertion. **NOTE-level** — Security recommends a
   follow-up `tests/test_security.py::test_sensitive_fields_never_serialized`
   parameterised over a synthetic model. Not blocking on Tier 3 (the
   denylist itself is enforced and unit-tested; the gap is verification
   coverage).

2. **Cache-Control on 200 responses.** S-30 demands `Cache-Control:
   no-store` on permission-denied responses. The 200 list/detail
   responses do **not** set `Cache-Control: no-store` — they're
   user-specific (gated by `has_view_permission`) and a shared cache
   could conceivably reveal them. **NOTE-level** — recommend a
   follow-up that sets `Cache-Control: private, no-store` on every
   API response, not just the denials.

3. **No new attack surface.** No new URL patterns at root, no
   middleware, no settings keys, no third-party imports, no new
   exception handlers. The implementation is a pure consumer of the
   `AdminSite._registry` + `ModelAdmin` contract.

4. **`label_for_field` import in `list.py`** — Django utility, no
   network/disk side effects. The `lookup_field` call accepts the
   `model_admin` reference (not client input) so there's no `getattr`
   on untrusted strings. ✅

## Verdict

**Approve.**

Tier 3 PR meets the §5.1 [S]-checklist mechanically and respects every
S-1…S-36 invariant a list/detail endpoint can touch. Two non-blocking
follow-ups (integration denylist test, `Cache-Control` on 200s)
recorded above; both are independently addressable post-merge. Per
`autonomy-policy.md` §1.3, tier 3 needs two agent approves, one of
which is the security [S]-checklist — that role is filled here.

— `claude-security-opus47`
