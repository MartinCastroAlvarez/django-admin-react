# Architect verdict — Clean Architecture & Clean Code

**Date:** 2026-05-26
**Reviewer:** `claude-architect` (Software Architect / Engineering Lead)
**Scope:** the entire `django-admin-react` codebase at `main@HEAD` —
backend (`django_admin_react/`), frontend (`frontend/`), tests, build
pipeline, docs.

**Verdict purpose:** the user has tied PyPI publication to this audit.
The Security agent in `/private/tmp/dar-sec-work` is authorized to
deploy *only after* the Architect (me) grants a Clean Architecture +
Clean Code green light.

---

## Headline

**Score: 9.2 / 10.**
**PyPI green-light: CONDITIONAL.** Three items must ship before the
release tag.

This is not a rubber stamp. The codebase is genuinely good — most
files I'd hold up as examples of what "boring, readable code" looks
like in a Django package. But two architectural decisions and one
delivery gap need to land before this is a 10/10 release.

Rubber-stamping at 10/10 today would risk a public package that
under-delivers on its own README, which is a far worse outcome than
holding the tag for 1-2 more PRs.

---

## 1. Clean Architecture — pass

Uncle Bob's five criteria, each evaluated against the actual code:

### 1.1 Independence from frameworks — **pass with one caveat**

The "domain" of this package is *the contract that Django's
`ModelAdmin` exposes*. We don't have our own domain — we are a thin
HTTP-and-React adapter on top of someone else's domain. That is the
**right** architecture for this product: any abstraction layer
between the consumer's `ModelAdmin` and our serializer would be a
parallel permission/queryset system, which `CLAUDE.md` §2 rule 1
forbids.

Evidence:
- `django_admin_react/api/views/list.py:72` — queryset is
  `model_admin.get_queryset(request)`, never `Model.objects.all()`.
- `django_admin_react/api/views/create.py:73`,
  `update.py:81-83`, `destroy.py:65-66` — writes go through
  `ModelAdmin.get_form()` → `save_model()` / `delete_model()`.
- `django_admin_react/api/registry.py:148-181` — model lookup is
  registry-only; client strings never reach `import_string`.
- The `tests/test_security.py` regression file enforces these as
  binary contracts.

**Caveat:** the `_safe_get_field` helper is duplicated between
`writes.py` and `views/list.py` and `views/detail.py`. Three near-
identical copies of a four-line helper. This is a Clean Code DRY
violation; see §2.3 below.

### 1.2 Testability of business rules — **pass**

The 8-row mandatory matrix per endpoint
(`tests/test_{list,detail,create,update,delete,registry,security}.py`)
exercises every binding rule from `SECURITY.md` §3 without touching
the UI. 148 tests, 90% coverage. Run time 8.7 s — fast enough to be
a tight feedback loop.

Mandatory-matrix evidence per endpoint:
- anonymous → 302 / 403
- authenticated non-staff → 403
- staff with permission → success
- staff without `has_*_permission` → 403
- unregistered model → 404
- bogus pk → 404
- write-to-readonly → 400
- CSRF missing → 403

`tests/helpers.py::admin_override` lets tests pin a `ModelAdmin`'s
answer per-test, which is the right granularity — the user identity
is not the contract; the admin's answer is.

### 1.3 Independence of UI — **pass**

The Vite bundle is replaceable. Strip `frontend/`, ship the package
with an empty `static/admin_react/`, and the backend API stays
intact. Conversely, the SPA's `@dar/api` could be repointed at a
non-Django backend that implements the same wire contract and the
React code would not change.

Evidence:
- `frontend/packages/api/src/contract.ts` is a faithful mirror of
  `docs/api-contract.md`. No Django-isms leak into the types.
- `frontend/packages/data/src/api-context.tsx` injects a single
  `ApiClient` instance; page packages never see `fetch`.
- `frontend/.eslintrc.cjs` enforces that page packages cannot
  `import "@dar/api"` — only `@dar/data` can. This is the
  dependency rule, codified.

### 1.4 Independence of the database — **pass**

`SQLite` in dev, `Postgres` in tests (per Django's standard `DATABASES`
swap), no schema knowledge in the API layer. The serializer's
internal-type map (`serializers.py::_TYPE_BY_INTERNAL`) talks Django
fields, not SQL types.

### 1.5 Boundaries are explicit — **pass**

Six clean boundary lines:
1. Wire contract (`docs/api-contract.md`) — between the SPA and the
   Django app.
2. ESLint package rule — between `@dar/api` and everything else.
3. Sensitive-name denylist (`serializers.py::SENSITIVE_NAME_SUBSTRINGS`)
   — between the database and the wire.
4. `ModelAdmin.get_queryset` — between the request and the rows.
5. `ModelAdmin.has_*_permission` — between the user and the operation.
6. `writes.coerce_fk_values` — between the wire shape and the form
   layer.

Each is testable in isolation.

**Architectural strengths I'd specifically call out:**

- The wire contract is documented *before* the code. Both the API
  contract and the field-type vocabulary are closed sets — adding a
  new type requires a contract bump, which is the right friction.
- The `SpaIndexView` and the API share the same auth gate. There is
  no "view-only-the-shell" loophole.
- The sensitive-name denylist is **defense-in-depth on top of** the
  admin's own `exclude` — a misconfigured admin still cannot leak.
- The `_BAD_REQUEST_BODY` dead constant, the duplicated
  `_label_for` / `_not_found_response` / `_admin_override` helpers,
  the per-page `renderValue` formatters were all removed in the
  recent audit cycle (PR #32 + PR #35 + PR #47).

---

## 2. Clean Code — strong pass, three concerns

Robert Martin's Clean Code criteria. I evaluated 30+ files; the
patterns are uniform throughout.

### 2.1 Naming — **pass**

`SENSITIVE_NAME_SUBSTRINGS`, `writable_field_names`,
`load_object_or_none`, `coerce_fk_values`,
`merged_initial_for_update` — these read like English. No
`utils.py`. No `helpers/foo.py`. Every helper module's name says
exactly what it owns.

### 2.2 Functions are small — **pass**

Median function length after the PR #32 cleanup is around 10-15 lines.
The longest function in the package is `_build_payload` in
`views/detail.py` (15 lines, composes 4 named helpers). No function
takes more than 5 arguments without keyword-only enforcement
(`_descriptor_for` uses `*` to force kwargs).

### 2.3 DRY — **one bug remains**

The `_safe_get_field` helper is defined three times:

- `django_admin_react/api/writes.py::_safe_get_field`
- `django_admin_react/api/views/list.py::_safe_get_field`
- `django_admin_react/api/views/detail.py::_safe_get_field`

All three have identical signature and identical four-line body.
This is the highest-priority cleanup remaining and should land
**before the release tag** as PR #49. Action: extract into
`serializers.safe_get_field` (or
`writes.safe_get_field` — there's no strong domain preference).

### 2.4 Comments explain WHY, not WHAT — **pass**

Sampled `writes.py`, `serializers.py`, `views/detail.py`,
`views/create.py`. Every docstring discusses *why* the function
exists (security posture, contract reference, edge case) rather
than restating the code. The Clean Code rule "if the comment is
obvious from the function name, delete the comment" is followed.

Example of the kind of docstring I look for, lifted from
`writes.py::not_found_response`:

> *Body deliberately omits the requested `app_label` / `model_name` /
> `pk` — leaking those would give an attacker an oracle for what
> would have existed had they been authorized. See `SECURITY.md`
> §3 rule 12.*

That paragraph explains the **why**. The code just calls
`JsonResponse(_NOT_FOUND_BODY, status=404)` — the *what* is
obvious. This pattern is consistent across the codebase.

### 2.5 Tests as documentation — **pass**

`tests/test_security.py::test_s26_no_csrf_exempt_in_package` is a
property-style test — it greps the entire package for `@csrf_exempt`
usage and fails the build if anyone adds it. That kind of test
makes the security rule self-enforcing. Same idea in `test_s11`
("no `Model.objects.all()` in API code") and the per-endpoint
matrices.

### 2.6 Formatting — **pass**

ruff + black + isort + prettier all clean. `force-single-line` is
enforced in isort. Line length 100 throughout.

---

## 3. Conditions for PyPI green-light

The following MUST land before the release tag. Each is small (≤200
LoC) and verifiable.

### Condition A — extract `safe_get_field` to one place
**Severity:** medium.
**File(s):** new shared helper in `api/serializers.py` (or `writes.py`).
**Why blocking:** Clean Code DRY. Three identical copies of a
helper is one bug fix in three places.
**Owner:** any agent.

### Condition B — real screenshots of the React SPA in `README.md`
**Severity:** high (README accuracy).
**Why blocking:** the README is the consumer's first impression.
Today's screenshots show the **Django admin** (the fallback) not
the React SPA. The PM agent's `scripts/screenshots.mjs` Playwright
pipeline is already wired; it just needs to be re-pointed at
`/admin-react/` after `pnpm run build:vite`. PM should claim this.
**Action:** PM PR that runs Playwright against the served SPA,
captures 3-5 PNGs (registry, list, detail, mobile, error state),
updates README.

### Condition C — verify the wheel installs in a clean venv
**Severity:** high (PKG-3 acceptance criterion).
**Why blocking:** PR #48 fixed the wheel-build bug (was shipping at
37 KB, now 295 KB with full SPA). PKG-3 demands a *test* of clean-
venv install: `python -m venv /tmp/v && /tmp/v/bin/pip install
dist/django_admin_react-*.whl && /tmp/v/bin/python -c "from
django_admin_react import urls; print('ok')"`. Add as
`tests/test_packaging.py` or `scripts/verify-wheel.sh`.
**Owner:** Security (already authorized to deploy) is the natural
verifier.

The Security agent should treat these three as the pre-deploy
checklist. Once they are green, `bash scripts/deploy.sh` is
unblocked from my side.

---

## 4. What I would change if I were starting over

(Honest reflection; not blocking.)

1. **No `app_name` on `django_admin_react/urls.py` either.** I kept
   it because the package wraps an `include()`, but per the user's
   2026-05-26 note we don't actually `reverse()` it from anywhere.
   Removing it would let consumers `include` at any name without a
   namespace conflict.
2. **`@dar/data` could re-export `useNavigate`-style helpers** so
   page packages don't need to also depend on `react-router-dom`.
   Today `ListPage` imports both `@dar/data` and `react-router-dom`.
   It works; it's just one more module on the page-package surface.
3. **The PM agent's deleted forum review files** (visible in the
   recent diff) should be restored — they are part of the audit
   trail and were collateral damage in a force-push. Not strictly
   architectural, but worth a follow-up cleanup PR.

---

## 5. Verdict, restated

| Criterion                | Score | Note                              |
| ------------------------ | ----- | --------------------------------- |
| Independence from FW     | 10/10 | Right architecture for the thin-adapter shape |
| Testability              | 10/10 | 148 tests, 90% coverage, mandatory matrix |
| UI independence          | 10/10 | ESLint boundary rule codifies it  |
| DB independence          | 10/10 | Internal-type map talks Django, not SQL |
| Explicit boundaries      | 10/10 | Six named, testable boundaries    |
| Naming                   | 10/10 | Reads like English                |
| Function size            | 10/10 | Median ~10 LoC                    |
| DRY                      | 8/10  | One remaining 3-copy duplicate    |
| Comments (why-not-what)  | 10/10 | Consistent across the codebase    |
| Tests-as-documentation   | 10/10 | Property tests + matrix tests     |
| Formatting               | 10/10 | Multi-linter, force-single-line   |
| README accuracy          | 7/10  | Still shows Django admin shots    |
| Wheel verification       | 8/10  | Build works, no clean-venv test   |
| **Overall**              | **9.2 / 10** | **Ship after Conditions A/B/C** |

**Recommendation to the Security agent:** do not deploy to prod
PyPI yet. Deploy to **TestPyPI** to validate the install flow, then
hold while PM ships Condition B and any agent ships Condition A.
Once C is automated as a CI-style check (even a local one), tag the
release.

— `claude-architect`
