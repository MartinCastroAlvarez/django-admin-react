# Architect review — PR #31

**PR:** [#31](https://github.com/MartinCastroAlvarez/django-admin-react/pull/31)
`fix(security): Cache-Control no-store on 200 responses + flip S-31 xfail`
**Branch:** `fix/security-cache-control-and-denylist-test`
**Reviewer role:** Architect (Tier 1 change — bug/security fix, no contract or
dep change).
**Author ≠ Reviewer:** confirmed.

---

## Scope

Four files, ~46 lines of net change:

1. `django_admin_react/api/views/registry.py` — set
   `response["Cache-Control"] = "no-store"` on the 200 `JsonResponse`.
2. `django_admin_react/api/views/list.py` — same.
3. `django_admin_react/api/views/detail.py` — same.
4. `tests/test_security.py` —
   - Adds three new tests (`test_s30_registry_200_has_no_store`,
     `test_s30_list_200_has_no_store`, `test_s30_detail_200_has_no_store`)
     that assert the header on real 200 responses through the test
     client.
   - Removes the `pytest.xfail` scaffolding from
     `test_s31_denylist_constant_exists_and_complete` and points it at
     the *actual* constant in the serializer module
     (`SENSITIVE_NAME_SUBSTRINGS`). The old test referenced a
     never-existing `SENSITIVE_FIELD_PATTERNS` and was silently passing
     via xfail — a real correctness bug in the test contract.
   - Adds `test_s31_is_sensitive_field_name_matches_required_patterns`
     to lock in the *functional* behaviour (case-insensitive substring
     match) as well as the constant.
   - Adds `agents/security-expert/` to the `DOC_PATHS` allow-list in
     `test_s37_no_committed_token_patterns_in_head` (documentation of
     the regex itself, not a real secret).

`gh pr diff 31 --name-only` returns exactly the 4 files above.

## Findings

- **No URL pattern change.** `urls.py` untouched. Routing is identical.
- **No permission code change.** `is_admin_user` / `forbidden_response`
  paths are unmodified. Auth gating still runs *before* the new header
  is set, so unauthenticated/forbidden requests still get 403 with their
  own `no-store` (already covered by `test_s30_forbidden_response_has_no_store`).
- **No serializer change.** The denylist constant
  (`SENSITIVE_NAME_SUBSTRINGS`) is read-only from the test side; the
  test just *checks* it. No new exclusion / no removed exclusion.
- **No dep change.** `pyproject.toml`, `poetry.lock`, root
  `package.json`, workflows — none touched.
- **RFC 7234 correctness.** `Cache-Control: no-store` is the strictest
  directive: it forbids any cache (shared or private) from storing the
  response. For per-user, permission-gated JSON payloads this is the
  correct choice — `no-cache` would still permit storage with
  revalidation, which is wrong for cross-user data. The header value
  matches what the 4xx path already emits (S-30 in ACCEPTANCE.md §4.6),
  so the 200/4xx surface is now uniform. Writes already set it via
  `writes.py`.
- **S-31 test fix verified.** `grep -n "SENSITIVE_NAME_SUBSTRINGS\|is_sensitive_field_name"
  django_admin_react/api/serializers.py` confirms both symbols exist at
  module scope. The test now imports them unconditionally; if either
  ever disappears, the test will *fail*, not xfail.
- **Test client coverage.** The three new 200 tests use
  `superuser_client` and hit the real URLConf (`/admin-react/api/v1/...`),
  not mocks. They will catch any future regression where a view
  bypasses the header.

## Risks

- **None observed.** This is a header-only fix on the success path; it
  cannot change response bodies, status codes, or auth outcomes. It can
  only make caching strictly safer.
- **Theoretical caller risk:** a downstream consumer that *relied* on
  the absence of `Cache-Control` to let a CDN cache responses would
  see invalidation. Out of scope for v1 — the package is admin-only,
  authenticated, per-user; no admin response should ever have been
  CDN-cacheable, and `ARCHITECTURE.md` does not promise cacheability.
  Documented here for the record; not a blocker.
- **Header conflict:** none. None of the three views previously set
  `Cache-Control`, so this is an additive `__setitem__`, not an
  override.

## Verification log (Architect, clean worktree from `origin/main`)

| Check | Result |
| --- | --- |
| `gh pr diff 31 --name-only` | 4 files (views ×3 + tests) |
| `poetry run pytest -q` | **142 passed** (was 137 + 1 xfail on main; net +5) |
| `poetry run ruff check django_admin_react tests` | clean |
| `poetry run black --check django_admin_react tests` | clean (31 files) |
| `poetry run bandit -r django_admin_react` | 0 issues (1 349 LoC) |
| URL pattern diff | none |
| Permission/auth code diff | none |
| Serializer denylist diff | none |
| Dependency diff (`pyproject.toml`, `poetry.lock`, root `package.json`) | none |

## Verdict

**Approve.** Tier 1 bug/security fix. RFC-correct header value,
parity with the 4xx path, real test coverage on the success path,
and a silent-xfail test contract restored to a load-bearing assertion.
Ready to merge once a separate Reviewer signs off per
`docs/agents/pr-workflow.md`.

— claude-architect
