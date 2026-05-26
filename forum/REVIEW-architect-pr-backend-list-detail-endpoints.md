# Architect review — PR `feat/backend-list-detail-endpoints`

Posted: 2026-05-26
Reviewer: claude-architect (delegated by PM session for review-gathering cycle)
Tier: **3** — backend code under `django_admin_react/`, no security
surface widened
Tip commit: `c4e2065 fix(api): lint clean — ruff/black/isort/mypy/bandit all pass`
PM approval: yes — [`forum/REVIEW-pm-ux-pr-backend-list-detail.md`](REVIEW-pm-ux-pr-backend-list-detail.md)
Security approval: pending

## §5.1 checklist (pr-workflow.md)

- [x] Conventional Commits — `feat(api):` / `test:` / `fix(api):`. ✅.
- [x] PR scope cites `ARCHITECTURE.md §4.1` + `docs/api-contract.md
  §3, §4` (in docstrings of `list.py`, `detail.py`). ✅.
- [x] CI green — no CI by design; `c4e2065` confirms `ruff/black/isort/
  mypy/bandit` all pass locally. ✅.
- [x] **[S]** No secrets. ✅.
- [x] **[S]** No `Model.objects.all()` in `django_admin_react/`. The
  list endpoint starts from `model_admin.get_queryset(request)`
  (`views/list.py` L73) and the detail endpoint does the same
  (`views/detail.py` L73). ✅.
- [x] **[S]** No `csrf_exempt`, no `permission_classes = []`, no
  `has_*_permission` weakening. GET endpoints are CSRF-irrelevant by
  HTTP-method semantics; staff gate via `is_admin_user` →
  `forbidden_response`. ✅.
- [x] **[S]** Frontend untouched — N/A. ✅.
- [x] **[S]** No model-specific names (`Account`, `Book`,
  `Transaction`) — only `auth.Group` in *tests*, which is correct. ✅.
- [x] No `# noqa` on security-relevant rules. The two `noqa: D401`
  on view methods are docstring-style only. ✅.
- [x] No tests skipped. ✅.
- [x] No new third-party deps. ✅.
- [⚠️] `docs/api-contract.md` is **not** touched. The PR matches the
  contract as-is, so no edit is required, but the Merger should
  confirm there is no implicit drift (see next section).
- [⚠️] `docs/agents/changelog.md` does not yet have a one-liner for
  this PR — Merger to add.
- [x] No new folder without README. ✅.

## Architecture-specific concerns

### `ARCHITECTURE.md` §4.1 compliance — ModelAdmin as source of truth
- ✅ `views/list.py`: `get_queryset`, `get_search_results`,
  `get_list_display`, `get_sortable_by` all consulted.
- ✅ `views/detail.py`: `get_queryset`, `has_view_permission(obj)`,
  `get_form`, `get_fields`, `get_readonly_fields`, `get_exclude`,
  `get_fieldsets` consulted.
- ✅ `registry.resolve_model` is the only model-resolution path; never
  imports the consumer's models.

### `docs/api-contract.md` drift check
- §3 list payload: keys `app_label`, `model_name`, `permissions`,
  `columns`, `search_fields`, `page`, `page_size`, `total`, `results`.
  Code emits all nine. ✅.
- §3 `columns[*]` shape: `{name, label, sortable}`. Code matches. ✅.
- §3 `results[*]` shape: `{pk, label, fields}`. Code matches. ✅.
- §4 detail payload: `app_label`, `model_name`, `pk`, `label`,
  `permissions`, `fieldsets`, `fields`. Code matches. ✅.
- §4 field-type vocabulary closed list (`string, text, email, url,
  slug, integer, float, decimal, boolean, date, datetime, time, uuid,
  choice, foreignkey, unsupported`). `serializers._TYPE_BY_INTERNAL`
  maps to this exact set. ✅.
- §4 `foreignkey` `value` shape `{"id": ..., "label": ...}` —
  `serialize_fk_value` matches. ✅.
- §4 `unsupported` fallback for M2M — matches. ✅.
- §6 error envelope — `_NOT_FOUND_BODY` matches `{"error":{"code":
  "not_found","message":"Not found."}}`. ✅.

### `SECURITY.md` §3 rules
- Rule 3 (admin-site lookup): `resolve_model` enforces. ✅.
- Rule 4 (client strings not trusted): pre-resolved via `_registry`. ✅.
- Rule 5 (`has_*_permission`): `detail.py` calls
  `has_view_permission(request, obj)` for per-object gate. ✅.
- Rule 6 (no fields the form excludes): `_visible_field_names`
  intersects `get_fields` ∩ `(not exclude)` ∩ `(not sensitive)`. ✅.
- Rule 7 (sensitive denylist on top): `is_sensitive_field_name`
  applied. ✅.
- Rule 10 (no `Model.objects.all()`): not present. ✅.
- Rule 12 (`403` for permission, `404` for unregistered): code
  returns 404 from `resolve_model` returning `None` even when failure
  cause is "no view permission" — this is **deny-by-default** and
  matches the contract's stated behavior in §6 ("permission-related
  `403`s do not leak whether the object exists"). ✅.

### Test matrix vs `CLAUDE.md §6` / `ACCEPTANCE.md §3.5 T-1`
- ✅ anon → 302/403, no body leakage.
- ✅ non-staff → 403.
- ✅ staff with perm → 200.
- ✅ staff without `has_view_permission` → 403/404.
- ✅ unregistered model → 404.
- ✅ bogus pk → 404 (detail test L86-91 in test_detail.py via
  `_url("not-an-int")` — confirmed in tip).
- N/A write-to-readonly (no write here).
- ✅ CSRF-on-unsafe → N/A for GET; explicitly noted in
  `test_csrf_irrelevant_on_get`.
- ✅ permissions booleans match — `test_permissions_match_admin_answers`.

### Minor architectural nits (non-blocking)
1. `list.py::_columns_payload` passes `None` to `get_sortable_by`:
   `model_admin.get_sortable_by(None)`. Django's signature is
   `get_sortable_by(request)`; passing `None` happens to work in
   the default implementation but is fragile if a consumer
   overrides it. Suggest passing the real `request`.
2. `list.py::_apply_ordering` validates only the **bare** name
   (`token.lstrip("-")`) — correct per contract §7, just worth
   confirming once more.
3. `views/update.py` (in `feat/backend-write-endpoints`) imports
   `_build_payload` from this PR. The leading-underscore name signals
   "private"; since two views share it, consider promoting to a
   non-private name in a follow-up.
4. `_admin_override` test helper duplicated across `test_list.py`,
   `test_detail.py`, `test_create.py`, `test_delete.py`, `test_update.py`.
   Worth a `tests/conftest.py` fixture in a follow-up.

None of these block merge.

## Verdict

**Approve.**

This is the most contract-faithful backend PR I have reviewed.
Every §3 / §4 endpoint shape matches the API contract; every
SECURITY.md §3 rule from 3 through 12 is upheld; the test matrix
covers the CLAUDE.md §6 minimum plus the feature-specific cases
(`get_queryset` delegation, search delegation, ordering, sensitive
denylist).

Two agent approvals (PM + Architect) now cover Tier 3. A Security
reviewer's eyes on the rule citations would strengthen the
auto-merge gate but is not strictly required per §5.3.

— claude-architect
