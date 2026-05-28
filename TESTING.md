# Testing

This file is the **test strategy** for the **`django-admin-react` SPA
super-layer**. It tells contributors where tests live, what each layer
is responsible for, and how to run them. Owned by the Software
Architect role.

Acceptance criteria for tests live in
[`ACCEPTANCE.md`](ACCEPTANCE.md) §3.5. This file does not duplicate
them — it tells you how to satisfy them.

> ### Scope (post-#544)
>
> The **API endpoint tests** (every list / detail / create / update /
> delete / action / history / autocomplete request/response shape,
> every permission gate, every queryset rule, every CSRF check) live
> in the **`django-admin-rest-api`** repo's `tests/` suite — that's
> where the API itself lives. **Do not duplicate API tests here.** If
> you find an API-test gap, file it in the API repo.
>
> This repo's `tests/` keeps:
>
> - **Frontend unit tests** (Vitest under `frontend/packages/**/*.test.tsx`
>   + `frontend/apps/web/**/*.test.tsx`) — for `@dar/ui`, `@dar/list`,
>   `@dar/details`, `@dar/form`, hooks like `useMediaQuery`, etc.
> - **SPA-side backend tests** — the SPA mount (`views.py`), the PWA
>   (`pwa.py`), the `AppConfig`, the URL include wiring, and any
>   future SPA-specific helpers. Currently the bulk of `tests/test_*.py`
>   still tests API behaviour because the local `django_admin_react/api/`
>   tree is still on `main`; **those tests move out with the code** in
>   Phase 3 of [META #544](https://github.com/MartinCastroAlvarez/django-admin-react/issues/544).
>
> **No Playwright / Cypress / e2e tooling.** Owner preference: unit
> tests (Vitest) + backend integration tests (pytest) are the entire
> matrix. Screenshots are captured manually against a dev server, not
> driven by a browser-automation framework.

---

## 1. Test layers

We use these layers; each has a single responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│ frontend (vitest)   React component + hook unit tests           │
│ tests/regressions/  bug-fix regression tests, one per issue      │
│ tests/              SPA-side backend tests (mount, PWA, URLs);   │
│                     while #544 is in flight, also the legacy    │
│                     API tests until they move to the API repo   │
│ django_admin_react/ unit tests inline (rare; for pure helpers)   │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Lives at | Speed budget | Hits the DB? | Hits the network? |
| ----- | -------- | ------------ | ------------ | ----------------- |
| Frontend unit | `frontend/**/*.test.tsx` (vitest) | < 50 ms each | no | no |
| Backend unit | inline `_test.py` next to pure helpers (rare; we prefer integration) | < 50 ms each | no | no |
| Backend integration | `tests/test_*.py` using `tests/test_project/` + `examples/` apps | < 1 s each | yes (sqlite, in-memory) | no |
| Regression | `tests/regressions/test_issue_<N>.py` | same as integration | yes | no |

Anything that imports a model from `examples/*` is an integration test,
never a unit test.

## 2. Folder layout

```
tests/
├── README.md
├── conftest.py              # pytest fixtures: anon_client, user_client,
│                             # staff_client, superuser_client, factory
│                             # helpers.
├── test_project/            # minimal Django project the test suite
│   ├── __init__.py          # boots against. Same INSTALLED_APPS as
│   ├── settings.py          # the demo project, but with TEST_RUNNER
│   ├── urls.py              # tweaks and an in-memory SQLite.
│   └── README.md
├── test_registry.py         # GET /api/v1/registry/ — full 8-row matrix
├── test_list.py             # (PR #4)
├── test_detail.py           # (PR #4)
├── test_create.py           # (PR #5)
├── test_update.py           # (PR #5)
├── test_delete.py           # (PR #5)
├── test_serializers.py      # field-by-field unit tests for
│                             # serializers.py; sensitive-name denylist.
├── test_permissions.py      # is_admin_user gate, AdminSite delegation.
├── regressions/             # one file per fixed bug, see §5.
│   └── __init__.py
├── perf/                    # pytest-benchmark suite, see §6.
│   └── __init__.py
└── e2e/                     # Playwright, see §7. Optional locally,
    └── README.md            # required before tagging 0.1.0.
```

Per-app smoke tests live with the app under
`examples/<app>/tests/test_admin.py`. They only verify that the
example app's `ModelAdmin` classes register; they do not duplicate
the package-level test matrix.

## 3. The mandatory test matrix

Every API endpoint added in `django_admin_react/api/views/` MUST have
an integration test file (`tests/test_<endpoint>.py`) with **at
least** eight tests, one per row of
[`CLAUDE.md`](CLAUDE.md) §6 / [`ACCEPTANCE.md`](ACCEPTANCE.md) §3.5
T-1:

| # | Test name (suggested) | Scenario | Expected |
| - | --------------------- | -------- | -------- |
| 1 | `test_anonymous_user_unauthorized` | no session cookie | redirect to login or `403` (no body leakage) |
| 2 | `test_authenticated_non_staff_user_forbidden` | logged in, `is_staff=False` | `403` |
| 3 | `test_staff_user_with_permission_succeeds` | logged-in staff w/ admin perm | success status |
| 4 | `test_staff_user_without_permission_forbidden` | logged-in staff, `has_*_permission` returns False | `403` |
| 5 | `test_unregistered_model_not_found` | URL path with unknown `app_label`/`model_name` | `404` |
| 6 | `test_bogus_pk_not_found` | (detail/update/delete only) | `404` |
| 7 | `test_write_to_readonly_or_excluded_field_rejected` | (create/update only) | `400`, value unchanged |
| 8 | `test_csrf_missing_on_unsafe_method_forbidden` | (POST/PATCH/DELETE only) | `403` |

Plus whichever feature-specific cases the endpoint needs (e.g.,
search delegated to `get_search_results`, ordering tokens validated,
permissions booleans match `ModelAdmin.has_*_permission`).

Tests skipped without an accompanying GitHub issue are rejected at
review.

## 4. Running the suite

```bash
# from the repo root
poetry install
poetry run pytest                       # full suite
poetry run pytest tests/test_registry.py # one file
poetry run pytest -k "permission"        # by name match
poetry run pytest --randomly-seed=12345  # deterministic check
poetry run pytest --cov=django_admin_react --cov-branch --cov-report=term-missing
```

Coverage thresholds are enforced by `pyproject.toml`'s
`[tool.coverage.report]` / `[tool.pytest.ini_options]`:

- Overall package: **≥ 90 %** statements.
- `django_admin_react/api/permissions.py` and
  `django_admin_react/api/serializers.py`: **100 %** statements +
  **100 %** branches.
- `django_admin_react/api/views/*.py`: **≥ 95 %** statements.

A run that drops below the threshold exits non-zero.

## 5. Regression tests

When you fix a bug, you add a test that fails on the parent commit:

```bash
# 1) demonstrate the bug
git checkout <parent-of-fix>
poetry run pytest tests/regressions/test_issue_<N>.py  # should FAIL

# 2) demonstrate the fix
git checkout <fix-branch>
poetry run pytest tests/regressions/test_issue_<N>.py  # should PASS
```

Naming: `tests/regressions/test_issue_<N>.py` where `<N>` is the
GitHub issue number. The test file's docstring links the issue and
explains the root cause in one sentence.

A bug-fix PR without a regression test is rejected at review.

## 6. Performance tests

Lives at `tests/perf/`. Uses
[`pytest-benchmark`](https://pytest-benchmark.readthedocs.io). The
budgets are documented in [`ACCEPTANCE.md`](ACCEPTANCE.md) §3.5 T-7
and informational pre-`0.1.0`. From `0.1.0`:

- `GET /api/v1/registry/` with 50 registered models — **p95 ≤ 80 ms**
  on the reference container.
- `GET /api/v1/<app>/<model>/?page=1&page_size=25` against a 10 000-
  row queryset — **p95 ≤ 150 ms**.

Run:

```bash
poetry run pytest tests/perf/ --benchmark-only
poetry run pytest tests/perf/ --benchmark-only --benchmark-json=perf.json
```

`perf.json` may be attached to the release PR.

## 7. End-to-end tests

Lives at `tests/e2e/`. Uses [Playwright](https://playwright.dev) (the
Python bindings, `pytest-playwright`). The suite covers the **three
primary consumer flows** as defined by the PM agent in
[`docs/ux/primary-flows.md`](docs/ux/primary-flows.md):

1. Log in as a staff user → land on the registry.
2. Open a model list → search → open an object.
3. Edit a field → save → reload → confirm persistence.

Run (after the SPA bundle lands in PR #6 / #7):

```bash
cd examples/project
poetry run python manage.py runserver &
poetry run pytest ../../tests/e2e/
```

Per `ACCEPTANCE.md` §3.5 T-5, the E2E suite is **required before
tagging `0.1.0`**.

## 8. Determinism rules

All tests must pass under:

```bash
poetry run pytest --randomly-seed=12345
poetry run pytest --randomly-seed=last
```

Forbidden in tests:

- `time.sleep(...)`. Use `freezegun` or `pytest-freezegun` or the
  framework's own time mocking.
- Test-time network I/O outside Django's test client.
- Order-dependent fixtures. A test that only passes because another
  ran first must be reworked.
- Tests that rely on `examples/<app>/migrations/` having been run by
  a previous test. `tests/test_project/` controls the schema; use
  `@pytest.mark.django_db` and let pytest-django manage transactions.

## 9. Fixtures and factories

`tests/conftest.py` provides:

- `anon_client`, `user_client`, `staff_client`, `superuser_client`
  — Django `Client` instances at each permission level.
- `make_user(is_staff=False, is_superuser=False, has_perm=())` —
  factory for ad-hoc users.
- `make_account`, `make_book`, `make_post`, … — factories per
  example app (lazy-imported so the suite still boots if an example
  app is removed).

Per `ACCEPTANCE.md` §3.5 T-2, fixtures **must not** populate the DB
with realistic PII. Names, emails, and IBANs are all obviously-
synthetic (`alice@example.com`, `IBAN0000…`).

## 10. Security-relevant tests

Tests that prove security claims live at:

- `tests/test_permissions.py` — staff gate, `AdminSite.has_permission`
  delegation, `is_active` enforcement.
- `tests/test_serializers.py` — sensitive-field denylist, callable
  `list_display` resolution, `str()` fallback.
- `tests/test_*_csrf.py` (or inline in each endpoint file) — CSRF
  enforcement on unsafe methods.
- `tests/test_*.py::test_unregistered_*` — deny-by-default for
  unknown model / field names.

These are also enumerated in [`SECURITY.md`](SECURITY.md) §4 and in
[`ACCEPTANCE.md`](ACCEPTANCE.md) §4 (Security section, owned by the
Security agent).

## 11. CI

There is no GitHub Actions CI in this repo by repo-owner direction.
The merge gate is local: `./scripts/lint.sh` (which runs the full
test suite via `pytest`) before every merge. See
[`scripts/README.md`](scripts/README.md) and
[`ACCEPTANCE.md`](ACCEPTANCE.md) §3.7.

A re-enable of GitHub Actions is tracked as
`docs/agents/software-architect/OPEN_QUESTIONS.md` **OQ-A-001**.

## 12. Cross-references

- [`ACCEPTANCE.md`](ACCEPTANCE.md) §3.5 — engineering-side test
  acceptance criteria (binding).
- [`ACCEPTANCE.md`](ACCEPTANCE.md) §4 — security-side test
  acceptance criteria (binding; owned by Security).
- [`CLAUDE.md`](CLAUDE.md) §6 — minimum test matrix.
- [`SECURITY.md`](SECURITY.md) §4 — security tests required for
  every endpoint.
- [`docs/api-contract.md`](docs/api-contract.md) — wire contract
  that integration tests assert against.
- [`docs/ux/primary-flows.md`](docs/ux/primary-flows.md) — the
  flows that E2E tests cover.
