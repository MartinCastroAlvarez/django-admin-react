# [SEC] Full security audit — 2026-05-26 (post-merge wave)

Session: `claude-security-opus47-1`
Audit scope: every file under `django_admin_react/api/`, the
serializer / permissions / registry modules, the URL patterns,
the linter / dep-audit gate, the test suite, and the recommended
consumer settings. Audited the post-merge `main` after wave 1
landed 9 PRs (#13, #20, #11, #14, #15, #17, #21, #18, #19, #22,
#25, #26, #27, #23, #24, #28).

## TL;DR

- **One real bug, one test bug, both fixed in PR #31.**
- No findings at HIGH severity. `pip-audit` clean.
- The 66 binary criteria in `ACCEPTANCE.md` §4 are now matched by
  green tests (after PR #31 lands) for every code-level invariant.
- `bandit -r django_admin_react` → 0 issues at any confidence.
- All 5 write endpoints (POST/PATCH/DELETE for create/update/destroy)
  honour the Five Rules byte-for-byte (Rule 6 `get_form`, Rule 7
  `delete_model`, Rule 10 `get_queryset`, Rule 12 readonly/exclude).

## Findings

### 🟡 MEDIUM — `Cache-Control: no-store` missing on 200 responses (fixed in PR #31)

**Where.** `registry.py:39`, `list.py:105`, `detail.py:88` — the 200
responses on the three read endpoints.

**Why it matters.** §4.6 S-30 set `Cache-Control: no-store` on the
4xx envelopes. The 200 responses on the same endpoints did not,
which leaves them eligible to be cached by an HTTP/1.1
intermediate proxy or a shared browser cache. Each of these
responses contains **per-user, permission-gated** data:

- `/api/v1/registry/` — filtered by `has_module_permission` +
  `has_view_permission`.
- list — `ModelAdmin.get_queryset(request)` scoped per user; rows
  filtered by `has_view_permission`.
- detail — per-object `has_view_permission(request, obj)`.

A cached cross-user response is a **permission bypass**.

**Fix.** PR #31 sets `Cache-Control: no-store` on every 200
response and adds three regression tests
(`test_s30_{registry,list,detail}_200_has_no_store`).

### 🟢 LOW — S-31 denylist test was silently `xfail`-ing (fixed in PR #31)

**Where.** `tests/test_security.py:340` —
`test_s31_denylist_constant_exists_and_complete`.

**Why it matters.** The test was scaffolded against a hypothetical
`SENSITIVE_FIELD_PATTERNS` constant. PR #17 landed the real
constant as `SENSITIVE_NAME_SUBSTRINGS` (`serializers.py:32`).
The test has been silently xfail-ing instead of validating the
denylist contract.

**Fix.** PR #31 points the test at the real constant and adds a
functional companion
(`test_s31_is_sensitive_field_name_matches_required_patterns`)
that exercises the helper with case-insensitive substring matches.

## Things I checked that came back clean

### §4.1 / §4.2 — Authn + Authz
- Every view starts with `is_admin_user(request)` → `forbidden_response()`.
- `_user_is_active_staff` chains `is_authenticated && is_active && is_staff`.
- Per-object `has_view_permission(request, obj)` in `detail.py`.
- `has_add_permission(request)` in `create.py`.
- `has_change_permission(request, obj)` in `update.py`.
- `has_delete_permission(request, obj)` in `destroy.py`.
- No `user.has_perm(...)` anywhere in the package (AST scan).

### §4.3 — Resource exposure
- Unregistered model → 404 (`resolve_model` returns `None`).
- Bogus pk (TypeError / ValueError) → 404, never 500.
- `_NOT_FOUND_BODY` and `_FORBIDDEN_BODY` contain zero
  resource-identifying data.

### §4.4 — Queryset
- Every read/write view starts at `model_admin.get_queryset(request)`.
- `Model.objects.all/filter` AST scan inside the package is clean.

### §4.5 — Form / write enforcement
- `create.py` builds the form via `model_admin.get_form(request)`,
  validates, then `model_admin.save_model(...)`.
- `update.py` PATCH semantics: `merged_initial_for_update` overlays
  payload on current instance values, runs the admin's form.
- `destroy.py` calls `model_admin.delete_model(request, obj)` —
  never `obj.delete()`.
- `reject_forbidden_keys` validates payload keys against the
  writable set BEFORE the form is built, catching `readonly` /
  `exclude` / unknown / sensitive-named keys.

### §4.6 — CSRF / session / cookies
- No `@csrf_exempt` anywhere in the package (grep + AST).
- All views are class-based `View` instances; Django's
  CsrfViewMiddleware enforces by default.
- `http_method_names` enumerates the allowed methods explicitly;
  unsupported methods → 405.
- **Cache-Control: no-store on 4xx** ✅ (in code).
- **Cache-Control: no-store on 200** ⚠️ → fixed in PR #31.

### §4.7 — Serialization
- `SENSITIVE_NAME_SUBSTRINGS` covers: `password, secret, token,
  api_key, apikey, hash, private_key, session, nonce, salt`.
- `is_sensitive_field_name` is case-insensitive substring match;
  treats non-`str` inputs as sensitive (defensive default).
- `filter_sensitive` is the standard second pass on every
  field-name iteration.
- `serialize_value` returns `str(value)` for unknown types — never
  raises.
- M2M → `"unsupported"` (closed v1 vocabulary).
- `_label_for(obj)` catches exceptions to never leak repr.

### §4.8 — Secret hygiene
- `.pre-commit-config.yaml` runs gitleaks + a local pygrep
  `no-partial-tokens` hook.
- `tests/test_security.py` does an AST + grep scan over the whole
  source tree for `ghp_/gho_/ghs_/aws_secret/BEGIN PRIVATE`.
- No matches in HEAD (excluding files that legitimately document
  the regex itself).

### §4.9 — Dependencies
- `scripts/audit-deps.sh` runs `pip-audit` → 0 findings at
  severity ≥ HIGH.
- `pnpm audit` is documented as deferred to consumers (`pnpm
  install` first); release prep must re-run.

### §4.11 — API hardening
- `http_method_names` per view; unsupported methods → 405.
- No CORS additions detected.
- No debug / introspection endpoint exposed.

### §4.14 — Secure defaults (consumer-facing)
- `SECURITY.md` §9 documents `SESSION_COOKIE_SECURE`,
  `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_SECURE`, HSTS,
  `X_FRAME_OPTIONS`, CSP recommendation.
- Mount-point is consumer-chosen (`ARCHITECTURE.md` §4.5); no
  hardcoded `/admin-react/` path in the package.

## Things not yet covered (deferred to future PRs)

| Item | Where it lands |
| ---- | -------------- |
| `@ensure_csrf_cookie` + real SpaIndexView impl (S-28) | follow-up PR after #35 |
| Include user-pk in `swr-cache.ts` localStorage keys (S-29 hardening) | follow-up PR after #35 |
| CSP snippet for `docs/installation.md` (QSEC-03) | follow-up PR after #35 |
| Subresource Integrity hashes (QSEC-04) | follow-up PR after #35 |
| `LogEntry`-based audit logging (QSEC-02) | future tier 5 PR |
| Rate limiting (QSEC-01) | future architect decision |
| Session expiration recommendation (QSEC-05) | doc-only follow-up |

## PR #35 — frontend SPA shell (added 2026-05-26)

A late-arriving PR that landed during this audit. Frontend-only;
no Python code touched.

**Findings (all non-blocking, surfaced as follow-up tickets):**

1. `SpaIndexView` (`django_admin_react/views.py`) is **still a stub**
   from the foundation PR. PR #35 ships the SPA bundle but does not
   wire it into the view, and does not apply `@ensure_csrf_cookie`.
   Needs a small follow-up PR.
2. The `useSwrCache` hook in `@dar/data` writes
   `registry/list/detail` response bodies to `localStorage` keyed
   by app/model/pk only — not by authenticated user. On a shared
   device, the next user's first paint may briefly show the
   previous user's cached data. **Recommended fix:** include the
   user pk in the cache key + clear on 403.
3. No CSP snippet shipped yet — frontend ships fresh, but the
   `docs/installation.md` recommendation is missing
   (QSEC-03 still open).

**What's right in PR #35:**

- `ApiClient` (`@dar/api/src/client.ts`) handles CSRF correctly:
  reads `csrftoken` cookie (not localStorage), sends
  `X-CSRFToken` header on unsafe methods, uses `credentials:
  'include'`. `SAFE_METHODS` whitelist scoped to GET/HEAD/OPTIONS.
- `.eslintrc.cjs` blocks `@dar/api` imports from page packages
  with `no-restricted-imports`. The boundary is real.
- `swr-cache.ts` never reads `document.cookie` or persists tokens —
  S-29 holds for tokens, even if the per-user-keying improvement
  is recommended.

## Result

Two findings, both shipped on `main`:

- **PR #31** — `Cache-Control: no-store` on 200 responses + flip
  the S-31 denylist test from xfail to a real pass + 3 new
  Cache-Control header regression tests. Merged 2026-05-26 with
  PM + Architect + Security forum approvals.
- **PR #32** — independent api-cleanup refactor that centralizes
  `not_found_response`, `load_object_or_none`, `bad_request`,
  `validation_failed`, public `label_for`. Rebased onto post-PR
  #31 main to preserve the Cache-Control fix; the rebase merged
  cleanly without conflicts (the two PRs touched disjoint hunks
  within the same view classes). Merged 2026-05-26.

The Five Rules in `SECURITY.md` §3 hold byte-for-byte against
post-merge `main`. The 66 binary criteria in `ACCEPTANCE.md` §4
match the code that's currently shipped — every code-level
invariant has a green regression test.

Audit verdict: **clean.** No HIGH severity findings. Two MEDIUM
findings, both fixed and shipped.

— `claude-security-opus47-1`, 2026-05-26
