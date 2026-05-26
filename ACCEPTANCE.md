# Acceptance criteria

This file defines the **measurable, testable** criteria the project
must meet to be considered "production-ready" by each owning role.

**Coordination protocol** — every agent role owns its own section:

- §2 **Product / UX** — owned by `claude-pm-ux-opus47` (this PR).
- §3 **Architecture / Engineering** — reserved for the Software
  Architect agent; do not edit from outside the role.
- §4 **Security / Compliance** — reserved for the Security agent;
  do not edit from outside the role.
- §5 **Release gate** — composite. May only be edited as part of a
  PR that touches §2/§3/§4 of this file.

If you are not the owning role, append your section below the
existing ones; do not edit another role's criteria. Cross-team
dependencies are stated explicitly with the "Depends on §X" prefix.

Every criterion is written so that a reviewer can answer **yes or
no** without subjective judgement. "Looks nice", "feels fast", and
"DX is good" are not acceptance criteria; they are vibes.

Source of truth: [`PRODUCT_VISION.md`](PRODUCT_VISION.md) §7 "Quality
bar" is the short version of §2 below. If the two disagree, this
file is authoritative and `PRODUCT_VISION.md` must be updated in the
same PR.

---

## 1. How to use this file

- Before merging a PR that the author believes finishes a milestone,
  the **Merger** reads §2/§3/§4 and confirms every relevant criterion
  is met.
- The release Merger (tier 6, human-gated) cannot tag a version
  unless §5 is fully green.
- "Not applicable to this PR" is a valid status only when justified
  in the PR description; an unjustified skip blocks the merge.

---

## 2. Product / UX acceptance criteria

Owner: `claude-pm-ux-opus47` (Product Manager / UX Lead).
Source: [`PRODUCT_VISION.md`](PRODUCT_VISION.md), [`docs/ux/`](docs/ux/)
(filled in subsequent PRs).

Statuses use the legend from [`PROGRESS.md`](PROGRESS.md): ✅ done · 🟡
in flight · ⬜ pending · ❌ blocked. Statuses are updated by the role
owner only.

### 2.1 Plug-and-play installation

| # | Criterion | How to verify |
| - | --------- | ------------- |
| P-1 | A Django developer can go from `pip install django-admin-react` to a working admin in **≤ 5 commands and ≤ 10 minutes** on a clean Django 5 project, following **only** the README. | Time a real installation on a clean venv against the [`ONBOARDING.md`](ONBOARDING.md) checklist. |
| P-2 | The required configuration is exactly: add to `INSTALLED_APPS` + `include("django_admin_react.urls")` at any URL prefix. **No other settings keys are required**. | Inspect [`django_admin_react/conf.py`](django_admin_react/conf.py): every key in `DEFAULTS` must have a working default. |
| P-3 | Installing the package **does not require Node, pnpm, or any frontend tooling on the consumer's machine**. The wheel ships the built SPA. | `pip install dist/*.whl` in an offline-Node environment; SPA renders. |
| P-4 | The package works at **any URL mount the consumer chooses** (`/admin/`, `/admin-react/`, `/staff/`, `/internal/foo/`). No hardcoded path strings in shipped code. | Run the test project at three different mount points; SPA links resolve correctly. |
| P-5 | Adding the package to `INSTALLED_APPS` **does not break the legacy HTML admin** at any other mount point. | Mount both at different prefixes; both work. |

### 2.2 Developer experience (Django dev, zero React)

| # | Criterion | How to verify |
| - | --------- | ------------- |
| D-1 | **No React code is required to expose a standard Django model in the SPA.** Registering a `ModelAdmin` is sufficient. | Test against the [`examples/`](examples/) apps; every registered model shows up. |
| D-2 | Customising `list_display`, `search_fields`, `readonly_fields`, `exclude`, and `has_*_permission` on a `ModelAdmin` **changes the SPA's behaviour on the next request**, without any frontend rebuild. | Toggle each on an example app; observe the SPA without redeploying. |
| D-3 | A consumer **never has to read or edit any file under `frontend/`** for any standard use case. | The README install path never references `frontend/`. |
| D-4 | Errors raised by the consumer's own `ModelAdmin` code surface with **the same traceback Django would show in the HTML admin** in `DEBUG=True`; never silently swallowed. | Add a raising `get_queryset`; observe traceback on detail. |
| D-5 | Every settings key is documented in `README.md` § "Configure" with type, default, and effect. | Diff [`django_admin_react/conf.py`](django_admin_react/conf.py) `DEFAULTS` against the README table. |

### 2.3 Onboarding

| # | Criterion | How to verify |
| - | --------- | ------------- |
| O-1 | The README's first **400 words** answer: what is this, who is it for, how do I install it, what do I get. No marketing intro. | Word-count the lead section; confirm content. |
| O-2 | A **screenshot grid** in the README shows: registry, list, detail, mobile detail, dark mode, login redirect. Each ≤ 200 KB optimised. | `docs/screenshots/` populated; README links resolve. |
| O-3 | [`ONBOARDING.md`](ONBOARDING.md) gives a five-minute happy-path **and** a "common pitfalls" section with three real failure modes (login redirect, mount conflict, missing migrations). | Reviewer with no project context follows it and succeeds. |
| O-4 | The first time a dev hits the SPA without being logged in, they are redirected to the existing Django admin login (`LOGIN_URL`), not to a custom login page. | Manual: visit mount with no session. |
| O-5 | The first time a dev hits the SPA logged in **without** `is_staff`, they get a clear "you need staff access" message — not a stack trace, not a blank page. | Manual: log in non-staff user; check response. |

### 2.4 Responsiveness

| # | Criterion | How to verify |
| - | --------- | ------------- |
| R-1 | All primary pages (registry, list, detail, create, edit, delete confirm) are **usable on viewports ≥ 375 px wide**. "Usable" = no horizontal page scroll, no overlapping interactive elements, no truncated labels without an accessible reveal. | DevTools responsive mode at 375 / 414 / 768 / 1024 / 1440 / 1920 px. |
| R-2 | Tables on the list page **adapt to narrow viewports** by collapsing into a vertical card list at < 640 px. Column order matches `get_list_display`. | Manual at 375 px. |
| R-3 | Form fields stack vertically and labels remain associated (no orphan placeholders) at < 640 px. | Manual at 375 px on the create page. |
| R-4 | Touch targets meet **44 × 44 px minimum** on touch devices (per WCAG 2.5.5). | Audit shipped components; report list. |
| R-5 | The SPA does **not** depend on hover-only interactions; everything reachable via hover is also reachable via focus / tap. | Disable hover styles; manual keyboard pass. |

### 2.5 Accessibility (WCAG 2.1 AA)

| # | Criterion | How to verify |
| - | --------- | ------------- |
| A-1 | Every interactive element has an accessible name (`aria-label`, label-element, or visible text) and a visible focus indicator with contrast ratio ≥ 3:1 against its background. | axe-core run + keyboard pass. |
| A-2 | Color contrast is **≥ 4.5:1** for normal text and **≥ 3:1** for ≥ 18 pt or bold ≥ 14 pt text, on both light and dark themes. | Automated contrast scan + spot-check. |
| A-3 | Every page is fully operable by keyboard alone, including modal dialogs (focus trap), the command palette (when shipped), and inline edit fields. | Keyboard-only walkthrough of the test matrix. |
| A-4 | Screen readers announce status changes (saved / failed / loading) via a polite live region. No silent failures. | NVDA / VoiceOver pass on the edit flow. |
| A-5 | All form errors are associated with their inputs via `aria-describedby` and presented in text (not only colour). | Inspect rendered DOM after a failed submit. |
| A-6 | The SPA respects `prefers-reduced-motion`: transitions ≤ 0 ms, no animated layout shifts. | Toggle the OS pref; observe. |
| A-7 | The SPA respects `prefers-color-scheme` on first paint (no light-mode flash before switching). | Cold load with dark OS preference. |

### 2.6 Documentation usability

| # | Criterion | How to verify |
| - | --------- | ------------- |
| Doc-1 | `README.md` is **≤ 350 lines** and links to deeper docs; it is not a kitchen sink. | `wc -l README.md`. |
| Doc-2 | Every code block in `README.md` and [`ONBOARDING.md`](ONBOARDING.md) **runs as-is** against the [`examples/`](examples/) project; no missing imports, no placeholder values like `<your-thing>`. | Manual replay. |
| Doc-3 | Every documented API endpoint in [`docs/api-contract.md`](docs/api-contract.md) has a happy-path example. | Diff endpoint table vs. example blocks. |
| Doc-4 | Every folder under the repo root has a `README.md` (per [`CLAUDE.md`](CLAUDE.md) §1). | `find . -type d -not -path './.git*' -not -path './node_modules*'` and check. |
| Doc-5 | All cross-doc links resolve. | A link-check pass before each release. |

### 2.7 SPA navigation

| # | Criterion | How to verify |
| - | --------- | ------------- |
| N-1 | Navigation between any two primary screens (registry ↔ list ↔ detail) **never triggers a full page reload**. The URL changes, the document doesn't. | DevTools Network panel; expect only `fetch` requests. |
| N-2 | Browser **back / forward buttons** work and restore the previous page's scroll position. | Manual. |
| N-3 | The URL is the source of truth for state that should be shareable: app, model, pk, search query, page, ordering. Refreshing the page yields the same view. | Reload mid-flow; confirm. |
| N-4 | Deep links to a model that the user can no longer view (perm lost) render the standard "not found / forbidden" empty state, never an unrecoverable error. | Manual: revoke perm mid-session, reload. |
| N-5 | Authenticated session expiry inside the SPA results in a redirect to the Django admin login, not a silent JS error. | Force-clear the session cookie; click anything. |

### 2.8 Visual consistency

| # | Criterion | How to verify |
| - | --------- | ------------- |
| V-1 | All primary screens use **one** type scale, **one** spacing scale, **one** color token set (light + dark mirrors), and **one** focus ring style. Defined in [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md). | Component audit. |
| V-2 | All buttons share variants from a closed set (`primary`, `secondary`, `ghost`, `danger`). No one-off buttons. | Grep `frontend/packages/ui/` for `<button` declarations. |
| V-3 | All form inputs share the same border, focus, error, and disabled states. | Storybook-equivalent screen audit. |
| V-4 | All states (loading, empty, error, success) use a dedicated component from [`docs/ux/states.md`](docs/ux/states.md); no ad-hoc placeholders. | Grep for inline "Loading…" strings. |
| V-5 | Dark mode is not a CSS afterthought — every screen has a designed dark counterpart with adjusted (not just inverted) colors. | Manual side-by-side. |

### 2.9 Extensibility UX

The PM/UX contract for every row below is in
[`docs/ux/extensibility.md`](docs/ux/extensibility.md). Rows
E-6 / E-7 / E-8 / E-9 were promoted from §2.10 to §2.9 by the
2026-05-26 extensibility directive (`forum/UX-DIRECTIVE-extensibility-contract.md`).
Architect + Security co-sign before each row turns live (gates
called out per row).

| # | Criterion | How to verify |
| - | --------- | ------------- |
| E-1 | The extension surface is the `ModelAdmin` class; the SPA reflects the consumer's choices automatically. **No "register your model with the React app" step.** | Add a new `ModelAdmin` in an example; reload; appears. |
| E-2 | Hiding the **Add** button requires only `has_add_permission` to return `False`. The button disappears immediately on the next request. | Toggle on an example. |
| E-3 | Marking a field readonly requires only adding it to `readonly_fields` / `get_readonly_fields`. The field renders as text. | Toggle on an example. |
| E-4 | A `ModelAdmin` with `list_display = ("name", "balance", calc_total)` (mix of fields and callables) renders correctly without any client-side change. | Add to fintech `Account` example. |
| E-5 | A consumer can rebrand colours via a single `tailwind.config.js` extension targeting CSS variables, without touching React source. | Rebuild against an extended config; verify. |
| E-5a | Consumer can drop a `theme_css` file via `DJANGO_ADMIN_REACT["theme_css"]` and reload the SPA with no rebuild and no Django restart. (X-1, [`extensibility.md`](docs/ux/extensibility.md) §2.) | Edit the file, hit reload, see new colours. |
| E-6a | Adding `actions = [my_action]` to an existing `ModelAdmin` causes the SPA list page to show the action dropdown + checkbox column, with no frontend change. (X-2.) | Add `make_published` to `Account`; reload list page. *Architect signed off (2026-05-26) on the action invocation endpoint shape.* |
| E-6b | An action invocation respects `ModelAdmin.has_*_permission` server-side; the SPA does not even render the action if the user lacks the perm. (X-2.) | Toggle perm, observe. *Security signed off (2026-05-26) on the perm enforcement path; `len(pks) ≤ 1000` cap codified in the Security follow-up PR.* |
| E-6c | An action whose `short_description` is set shows that label in the dropdown; an action that raises an exception renders a toast with the message and never crashes the SPA. (X-2.) | Two example actions covering both paths. |
| E-7a | Adding `inlines = [BookInline]` to an existing `ModelAdmin` causes the SPA detail page to render the inline section, with no frontend change. (X-4.) | Add an inline to `Author`; open an author's detail. *Architect signed off (2026-05-26) on the inline payload shape.* |
| E-7b | Saving parent + inline edits hits the server as one atomic PATCH; a validation error on a child rolls back the parent. (X-4.) | Force a child validation error; confirm parent unchanged. |
| E-7c | A `StackedInline` renders as stacked, a `TabularInline` renders as tabular — the SPA respects the consumer's choice. (X-4.) | Two examples in `examples/library`. |
| E-8a | Returning a non-empty `get_detail_blocks(request, obj)` from a `ModelAdmin` causes the SPA detail page to render the blocks in their declared `placement` slot. (X-5.) | Add a `stats` block; observe. *Architect signed off (2026-05-26) on the block schema enum.* |
| E-8b | A block of an unrecognised `type` is silently dropped client-side and logged server-side. (X-5.) | Push a fake `type` in an example; observe console + server log. |
| E-8c | A block whose server-side computation fails renders an `ErrorState` scoped to that block; sibling blocks keep rendering. (X-5.) | Force a block to raise; observe. |
| E-9  | A `type: "html"` block runs through the configured server-side sanitiser (`nh3`) before reaching the SPA; `<script>` tags and inline event handlers never survive the round-trip. (X-6.) | Try to slip a `<script>` through; observe stripped output. **Security signed off (2026-05-26) conditional on C-1..C-10 in [`forum/REVIEW-security-pr-ux-extensibility-contract.md`](forum/REVIEW-security-pr-ux-extensibility-contract.md) §3.X-6.2** — the original `allow_unsafe_html=True` boolean was rejected, replaced with the constrained `trusted_html` block-type path (v1.x at earliest; PM/UX recommends no escape hatch in v1). E-9 stays **drafted, not live, until the Security follow-up PRs land** (sanitiser spec + implementation + CSP defaults). v0.1 ships with X-1..X-5 + X-7; X-6 is post-v0.1. |

### 2.10 v1 non-goals

These are **explicitly out of scope** for the v1 acceptance. Building
any of them does not affect §2.x readiness, and shipping them on the
side without an explicit v1.x roadmap entry is a regression.

> Edited 2026-05-26 by the extensibility directive: inlines, custom
> admin actions, server-rendered HTML, and custom widgets moved into
> §2.9 (rows E-6..E-9). The remaining items below stay out-of-scope.

- Autocomplete / `raw_id_fields`.
- ManyToMany editing (read-only stub only).
- React-side plugin / extension API.
- Server-rendered HTML *fallback pages* (HTML lives inside the SPA's `html` block type, not as a server-rendered fallback page).
- Runtime Tailwind config swap (CSS-variable theming only; `theme_css` per E-5a is opt-in but still file-based).
- Multi-`AdminSite` support (single configured site in v1).
- Internationalisation beyond `LANGUAGE_CODE` defaults (full i18n is v1.x).

### 2.11 Usability regression criteria

A regression is anything that **was acceptable in a previous merge and is
now not**. Before merging any PR, the reviewer confirms none of the
following degraded since the previous merge:

- Install time (P-1) did not increase by > 10 %.
- Lighthouse-equivalent FCP / LCP did not increase by > 200 ms on the
  reference profile.
- Number of clicks to reach any primary action did not increase.
- Number of required settings keys did not increase.
- Word count of `README.md` did not increase by > 10 % (gentle pressure
  to keep docs focused).
- Number of "must understand React to use this feature" code paths
  remained at zero.

If a regression is intentional and justified, the PR description must
say so explicitly and `PRODUCT_VISION.md` may need an update.

### 2.12 Documentation quality expectations

- Every product-facing doc states its **owner** at the top.
- Every product-facing doc has a "last reviewed" date no older than
  one minor version behind `pyproject.toml` `version`.
- Every documented behaviour has either a test in `tests/` **or** a
  reproducible manual step.
- No doc may reference a feature that does not exist yet without a
  "🟡 planned for v1.x" tag.

### 2.13 Dependencies on other roles

The following Product / UX criteria depend on engineering or security
deliverables. The PM/UX role does **not** sign these off alone.

- P-3 (no Node required) depends on `scripts/build.sh` correctly
  embedding the SPA bundle into the wheel — owned by Engineering.
- O-4 / O-5 (login redirect, non-staff message) depend on the auth
  gate in [`django_admin_react/api/permissions.py`](django_admin_react/api/permissions.py) — owned by Security.
- E-2 / E-3 (button hiding, readonly rendering) depend on the
  registry and detail endpoints exposing `permissions` and
  `readonly` flags correctly — owned by Engineering.
- N-5 (session expiry redirect) depends on `@dar/api` handling 401 /
  403 responses uniformly — owned by Engineering.

---

## 3. Architecture / Engineering acceptance criteria

Owner: Software Architect / Engineering Lead. Source of truth files:
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`PLAN.md`](PLAN.md),
[`TESTING.md`](TESTING.md) (to land in a follow-up PR),
[`API_CONTRACT.md`](API_CONTRACT.md) (or
[`docs/api-contract.md`](docs/api-contract.md) — top-level pointer to
land in the same follow-up PR).

Every criterion below is **binary** (yes / no) and **verifiable**
(reviewer can answer it by running a documented command or reading a
specific file). Subjective adjectives ("clean", "scalable",
"performant") are not used here.

### 3.1 Backend architecture (`django_admin_react/`)

| # | Criterion | How to verify |
| - | --------- | ------------- |
| B-1 | `ModelAdmin` is the sole source of truth. The package never registers consumer models, defines a parallel permission system, or maintains its own field registry. | `grep -RIn 'admin.site.register\|@admin.register\|class.*ModelAdmin' django_admin_react/` returns zero matches. |
| B-2 | All querysets start from `ModelAdmin.get_queryset(request)`. No `Model.objects.all()` or `.objects.filter(...)` outside of fixtures and tests. | `grep -RInE '\.objects\.(all\|filter\|get\|exclude)\(' django_admin_react/` returns zero matches. |
| B-3 | Writes go through `ModelAdmin.get_form()` and `ModelAdmin.save_model()`. Deletes go through `ModelAdmin.delete_model()`. No `setattr(obj, ...)` on client-provided keys. | Code review + a regression test per write endpoint asserting that an excluded field cannot be set via JSON. |
| B-4 | `django_admin_react/api/` has a fixed module shape: `permissions.py`, `registry.py`, `serializers.py`, `urls.py`, `views/` (one file per endpoint). No business logic in `urls.py`; no HTTP envelope work in `permissions.py` / `registry.py` / `serializers.py`. | File listing matches; each module's top docstring states its single responsibility. |
| B-5 | The admin site is resolved lazily on every request via `django_admin_react.conf`. No module-level capture of `admin.site`. | `grep -RIn 'admin.site$\|admin = admin.site\|site = admin.site' django_admin_react/` returns zero matches outside `conf.py`. |
| B-6 | CSRF is on for every unsafe method. No `csrf_exempt`, no `enforce_csrf_checks=False`. | `grep -RIn 'csrf_exempt\|enforce_csrf_checks=False' django_admin_react/` returns zero matches. |
| B-7 | Client-provided `app_label`, `model_name`, `pk`, and field names are resolved through the admin registry / `ModelAdmin.get_form()` before any DB or attribute lookup. Unknown values return `404` (model) or `400` (field), never `500`. | Tests B-7.a (unknown model) and B-7.b (unknown field) per write endpoint. |
| B-8 | Every public Python symbol in `django_admin_react/` has a docstring **and** a type annotation. "Public" = not prefixed with `_` and either in `__init__.py` `__all__` or referenced by `docs/api-contract.md`. | `mypy --strict` + a custom check (or `pydocstyle`) in `scripts/lint.sh`. |

### 3.2 Frontend architecture (`frontend/packages/`)

| # | Criterion | How to verify |
| - | --------- | ------------- |
| F-1 | Package responsibilities are respected exactly as defined in [`ARCHITECTURE.md`](ARCHITECTURE.md) §5.1. `@dar/ui` has no business logic; `@dar/api` is the only package that calls `fetch`; `@dar/data` is the only package that imports `@dar/api`. | ESLint rule (`no-restricted-imports`) configured per package + spot-grep. |
| F-2 | No circular dependencies between workspace packages. | `pnpm -r exec madge --circular src/` reports zero cycles. |
| F-3 | No model-specific identifier (e.g. `Account`, `Book`, `Transaction`) appears anywhere under `frontend/packages/`. The UI is metadata-driven. | `grep -RIn -E '(Account\|Transaction\|Statement\|Author\|Book\|Loan\|Post\|Comment\|Tag\|Category\|Product\|Order\|OrderItem\|Customer\|Employee\|Department\|Role)' frontend/packages/` returns zero matches. |
| F-4 | TypeScript is strict: `strict: true`, `noImplicitAny: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true` in `frontend/tsconfig.base.json`. No new `// @ts-ignore` or `// @ts-expect-error` without a same-line PR or issue link. | `cat frontend/tsconfig.base.json` + `grep -RIn '@ts-ignore\|@ts-expect-error' frontend/packages/` review. |
| F-5 | Tailwind config is build-time only. No client code dynamically rewrites `tailwind.config.js` or reads style tokens from network responses. | Code review. |
| F-6 | The built bundle (Vite output for `@dar/shell`) is copied to `django_admin_react/static/admin_react/` and `django_admin_react/templates/admin_react/index.html` by `scripts/build.sh`, and is included in the wheel. | §3.8 packaging tests cover this. |

### 3.3 Package modularity & dependency hygiene

| # | Criterion | How to verify |
| - | --------- | ------------- |
| M-1 | Imports flow inward in Python: `api/views/*` may import `permissions`, `registry`, `serializers`; the reverse is forbidden. | `grep -RIn 'from django_admin_react.api.views' django_admin_react/api/{permissions,registry,serializers}.py` returns zero matches. |
| M-2 | Each `frontend/packages/<name>/package.json` lists every cross-workspace dependency under `dependencies` (using `workspace:*`). No implicit hoisting. | JSON inspection. |
| M-3 | `poetry.lock` is in sync with `pyproject.toml`. | `poetry lock --check` exits 0. |
| M-4 | `frontend/pnpm-lock.yaml` is in sync with the workspace. | `pnpm install --frozen-lockfile` succeeds. |
| M-5 | New third-party Python dependency requires an entry in [`docs/agents/decisions.md`](docs/agents/decisions.md) and a clean `pip-audit`. | Diff review + audit. |
| M-6 | New third-party npm dependency in a generic package (`@dar/ui`, `@dar/api`, `@dar/data`) requires a decisions-log entry **plus** PR-body justification (size, license, last-maintained date). | Diff review. |
| M-7 | `pyproject.toml`'s runtime `[tool.poetry.dependencies]` lists at most: `python`, `Django`. Any other runtime dep needs a §3.7 release-gate review. | `pyproject.toml` inspection. |

### 3.4 API contract stability

| # | Criterion | How to verify |
| - | --------- | ------------- |
| C-1 | The wire contract lives in [`docs/api-contract.md`](docs/api-contract.md) (with a top-level [`API_CONTRACT.md`](API_CONTRACT.md) pointer per Architect role spec). Any request/response/error-code change updates the contract in the **same** PR. | Reviewer rejects API diffs that don't touch the contract file. |
| C-2 | Within `api/v1/`, only additive changes are permitted: new optional response fields, new optional query params. Renaming, removing, or retyping any existing field requires a new namespace (`api/v2/`). | Diff review against the previous tagged version. |
| C-3 | All endpoints return the documented error envelope: `{"error": {"code": "...", "message": "...", "fields": {...}?}}`. No bare strings, no default Django error pages, no stack traces. | Integration test per endpoint asserts envelope on the anonymous, 404, validation, and CSRF paths. |
| C-4 | Permission failures do not leak existence. `404` for unregistered models is acceptable; `403` for existing-but-forbidden is acceptable; `500` from a permission path is not. | Tests for both cases per endpoint. |
| C-5 | Pagination, ordering, and search contracts match [`docs/api-contract.md`](docs/api-contract.md) §7 exactly. `page`, `page_size`, `ordering`, `q` query params behave as documented; unknown ordering tokens are silently dropped, not 500. | Tests per endpoint. |

### 3.5 Testing requirements

Strategy and folder layout live in [`TESTING.md`](TESTING.md) (lands in
a follow-up PR; criteria are still binding once that file exists).

| # | Criterion | How to verify |
| - | --------- | ------------- |
| T-1 | Every API endpoint has integration tests covering the eight rows of the [`CLAUDE.md`](CLAUDE.md) §6 matrix (anonymous, non-staff, staff w/o perm, staff w/ perm, unregistered model, bogus pk, write-to-readonly, CSRF-missing). Each row is its own `def test_...`, not an assertion inside a mega-test. | Test count per endpoint ≥ 8. |
| T-2 | Coverage thresholds (enforced via `pyproject.toml`'s pytest-cov config): overall package ≥ **90 %** statements; `permissions.py` and `serializers.py` **100 %** statements and **100 %** branches; `views/*.py` ≥ **95 %** statements. | `poetry run pytest --cov=django_admin_react --cov-branch --cov-fail-under=90` exits 0. |
| T-3 | Tests are deterministic: no `time.sleep`, no test-time network I/O outside Django's test client, no order dependency. | `poetry run pytest -q` with `--randomly-seed=12345` and `--randomly-seed=last` both pass. |
| T-4 | Integration test suite lives under `tests/` and uses `tests/test_project/` plus the example apps in `examples/`. | `poetry run python tests/test_project/manage.py check` exits 0. |
| T-5 | End-to-end tests (Playwright or equivalent) cover the three primary consumer flows once the SPA lands: log in → registry, list a model with search, edit + save an object. Required before tagging `0.1.0`. | E2E suite under `tests/e2e/`; the runner is documented in [`TESTING.md`](TESTING.md). |
| T-6 | Every bug-fix PR adds a regression test in `tests/regressions/test_issue_<N>.py` (or equivalent) that fails on `main` before the fix. | Pre-merge replay of the new test on the parent commit fails; the same test on the PR head passes. |
| T-7 | Stress / performance tests live in `tests/perf/`. v1 budgets (informational; not merge-blocking until `0.1.0`): `GET /api/v1/registry/` with 50 models p95 ≤ **80 ms**; `GET /api/v1/<app>/<model>/?page=1&page_size=25` against a 10 000-row queryset p95 ≤ **150 ms**. | `pytest-benchmark` JSON output in the release PR. |
| T-8 | Frontend tests (added with PR #6/#7): `@dar/ui` component tests with ≥ 80 % branch coverage; `@dar/api` fetch-mocked unit tests for every hook; `@dar/data` tests for hydrate-from-localStorage, server reconcile, and the debounce buffer with fake timers. | Vitest run reports per-package coverage. |
| T-9 | Concurrency: any code path touching a transaction or session is exercised under `TestCase` (transaction-wrapped); paths using `select_for_update` run under `TransactionTestCase`. | Per-test class choice. |

### 3.6 Linting, formatting, typechecking

| # | Criterion | How to verify |
| - | --------- | ------------- |
| L-1 | `./scripts/lint.sh` exits 0 for every commit reaching `main`. The Merger records the result in the PR body or a forum status post. | PR body / forum check. |
| L-2 | `isort` runs with `force_single_line = true` (one import per line). | `poetry run isort --check-only django_admin_react tests` exits 0. |
| L-3 | `black` is the source of truth for Python formatting; `ruff format` is configured to match. | `poetry run black --check django_admin_react tests` exits 0. |
| L-4 | `mypy` is strict on the package. | `poetry run mypy django_admin_react tests` exits 0. |
| L-5 | TypeScript is strict (see F-4). `pnpm -r typecheck` exits 0. | Run output. |
| L-6 | `prettier --check` passes on the frontend. | `pnpm exec prettier --check "packages/**/*.{ts,tsx,js,jsx,json,md}"` exits 0. |
| L-7 | No `# noqa` on a security-relevant rule (per [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md) §4); no `# type: ignore` / `// @ts-ignore` without a same-line PR or issue link. | `grep -RIn '# noqa\|# type: ignore\|@ts-ignore' django_admin_react/ frontend/packages/` review. |

### 3.7 CI / quality pipelines

GitHub Actions are intentionally **off** per repo-owner direction. The
Merger runs the pipeline locally before squash-merge.

| # | Criterion | How to verify |
| - | --------- | ------------- |
| Q-1 | `./scripts/lint.sh` is the merge gate. A merge that bypassed it is a policy violation and a revert candidate. | Forum status / PR body. |
| Q-2 | `./scripts/build.sh` is the release gate. Both the SPA build and `poetry build` must succeed. | Run output before tagging. |
| Q-3 | A PR that touches `pyproject.toml` runtime deps, frontend root `package.json` deps, or `LICENSE` includes a locally-recorded `pip-audit` (Python) and `pnpm audit` (npm) clean run in the PR body. | PR-body inspection. |
| Q-4 | The "no CI" decision is revisited before leaving pre-alpha and recorded in [`docs/agents/decisions.md`](docs/agents/decisions.md). | Decision-log entry. |

### 3.8 Packaging

| # | Criterion | How to verify |
| - | --------- | ------------- |
| PKG-1 | `poetry build` produces both an `sdist` (`django_admin_react-X.Y.Z.tar.gz`) and a wheel (`django_admin_react-X.Y.Z-py3-none-any.whl`). | `ls dist/` after `./scripts/build.sh`. |
| PKG-2 | The wheel ships the pre-built React assets at `django_admin_react/static/admin_react/` and `django_admin_react/templates/admin_react/index.html`. | `python -m zipfile -l dist/*.whl \| grep -E '(static/admin_react/\|templates/admin_react/)'` lists those files. |
| PKG-3 | The wheel installs in a clean virtualenv without Node, without internet access to npm, and without dev dependencies. | `python -m venv /tmp/dar && /tmp/dar/bin/pip install dist/*.whl && /tmp/dar/bin/python -c "import django_admin_react"` exits 0. |
| PKG-4 | Metadata is canonical: `name = "django-admin-react"`, Python import `django_admin_react`, `requires-python = ">=3.10"`, `Django >=5,<6`. | `pyproject.toml` inspection. |

### 3.9 Documentation completeness

| # | Criterion | How to verify |
| - | --------- | ------------- |
| Doc-A | The required-reading set is present and consistent: [`README.md`](README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`PLAN.md`](PLAN.md), [`PROGRESS.md`](PROGRESS.md), [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CLAUDE.md`](CLAUDE.md), [`TESTING.md`](TESTING.md), [`API_CONTRACT.md`](API_CONTRACT.md) (or a top-level pointer to `docs/api-contract.md`), [`ACCEPTANCE.md`](ACCEPTANCE.md). | `ls` of repo root. |
| Doc-B | Every folder has a `README.md` (per [`CLAUDE.md`](CLAUDE.md) §1). | `find . -type d -not -path './.git*' -not -path './node_modules*' -not -path './.venv*' -not -path './dist*'` followed by per-dir `README.md` check. |
| Doc-C | Every architectural decision is recorded in [`docs/agents/decisions.md`](docs/agents/decisions.md) within the same PR. | PR diff review. |
| Doc-D | Every meaningful merge appends a one-liner to [`docs/agents/changelog.md`](docs/agents/changelog.md). | Diff review. |
| Doc-E | All internal markdown links resolve. | `lychee` or `markdown-link-check` is added to `./scripts/lint.sh` no later than `0.1.0` and runs against tracked `*.md` files. |

### 3.10 Backwards compatibility & semantic versioning

| # | Criterion | How to verify |
| - | --------- | ------------- |
| V-1 | `0.y.z` releases may break the public API between minor versions; from `1.0.0` SemVer applies strictly (MAJOR for breaking, MINOR for additive, PATCH for fixes). | Release-PR diff vs. previous tag, classified by the Architect. |
| V-2 | A deprecation lasts ≥ one minor cycle: a symbol marked `# deprecated` in `N.x` remains in `N.x+1` and may be removed in `N.x+2` or the next major. | Deprecation diff log in `CHANGELOG.md`. |
| V-3 | The wire contract is versioned by URL namespace (`api/v1/`, `api/v2/`). No breaking change is ever applied inside an existing namespace. | Diff review. |
| V-4 | Public Python API surface is exactly what is documented in [`docs/api-contract.md`](docs/api-contract.md) plus the package's top-level `__init__.py` exports. Anything else is private and may change without notice. | `__all__` / docs cross-reference. |

### 3.11 Extensibility

| # | Criterion | How to verify |
| - | --------- | ------------- |
| X-1 | Extension is through `ModelAdmin`, not by writing React. Toggling `readonly_fields`, `has_*_permission`, `list_display`, `search_fields`, `exclude` on a `ModelAdmin` changes the SPA on the next request, with no frontend rebuild. | Tests against the example apps. |
| X-2 | The package never registers consumer models. Model discovery is via `admin.site._registry`. | See B-1. |
| X-3 | No custom DSL (no YAML config, no plugin discovery, no metaclass registry). New behavior is added via `ModelAdmin` attributes or a documented `DJANGO_ADMIN_REACT` setting. | Architecture review. |
| X-4 | New `DJANGO_ADMIN_REACT` keys have a default in `django_admin_react/conf.py` `DEFAULTS` and are documented in the README configuration table. | Diff cross-check. |

### 3.12 Maintainability boundaries

| # | Criterion | How to verify |
| - | --------- | ------------- |
| MT-1 | No file in `django_admin_react/` exceeds **400 lines** without an accompanying refactor plan in [`docs/agents/open-questions.md`](docs/agents/open-questions.md). | `wc -l` per file. |
| MT-2 | No public function exceeds **60 lines** without an in-docstring justification (e.g., "kept long because Django expects this signature verbatim"). | Review. |
| MT-3 | Cyclomatic complexity (radon) ≤ **10** per function on average; exceptions documented. | `poetry run radon cc -a django_admin_react/`. |
| MT-4 | Tech debt is tracked in GitHub issues **and** linked from [`docs/agents/open-questions.md`](docs/agents/open-questions.md). Inline `# TODO` / `# FIXME` without a linked issue is rejected at review. | Grep + issue cross-reference. |

### 3.13 Architecture/engineering release-blocking checklist

A release is blocked by **any** of the following failing. The
Architect runs this checklist before tagging.

- [ ] T-2 coverage thresholds met on the release commit.
- [ ] L-1 `./scripts/lint.sh` exits 0.
- [ ] PKG-3 wheel install in a clean venv (no Node) succeeds.
- [ ] C-1 `docs/api-contract.md` is in sync with the implementation.
- [ ] F-2 no circular workspace dependencies.
- [ ] Doc-A required-reading docs all present and not stale.
- [ ] Doc-E markdown link checker clean.
- [ ] Q-3 `pip-audit` and `pnpm audit` clean.
- [ ] V-4 public API surface diff vs. previous tag reviewed against
      SemVer rules.

### 3.14 Dependencies on other roles

The following engineering criteria depend on PM/UX or Security
deliverables. The Architect does **not** sign these off alone.

- B-7 (no client-injected lookup hits the DB without resolving through
  the admin registry) is also a Security item; Security signs off on
  the test-matrix coverage.
- L-1 (lint gate) depends on `scripts/lint.sh` itself; the script's
  scope is Architect-owned but Security may add scanners.
- PKG-2 (wheel ships SPA bundle) depends on `scripts/build.sh`
  correctly emitting the Vite output; PM's P-3 (no Node required on
  consumer side) requires this.
- T-5 (E2E tests) requires the SPA to exist; PM's flow definitions
  inform what "primary flows" means here.

---

## 4. Security / Compliance acceptance criteria

Owner: Security & Compliance Lead. See
[`docs/agents/security-expert/AGENT.md`](docs/agents/security-expert/AGENT.md).
Source: [`SECURITY.md`](SECURITY.md), [`docs/api-contract.md`](docs/api-contract.md),
the threat model (`docs/threat-model.md`, planned).

> **The React admin inherits Django admin security guarantees; it
> never weakens them.** Every criterion in this section is binary —
> either a test passes or the release is blocked. "Looks secure" is
> not an acceptance criterion.

Statuses use the legend from [`PROGRESS.md`](PROGRESS.md): ✅ done · 🟡
in flight · ⬜ pending · ❌ blocked. Statuses are updated by the role
owner only.

### 4.1 Authentication

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-1 | Anonymous requests to any `/<mount>/api/v1/...` endpoint return **403** (or **302** to `LOGIN_URL` if the consumer's middleware redirects). No object data, model names, field names, app labels, or user identifiers appear in the response body or headers. | `tests/test_security.py::test_anonymous_rejected_for_every_endpoint`; assert response body is the canonical `{"error": {"code": "forbidden", ...}}` envelope with no model/field/app data. |
| S-2 | Authenticated users with `is_staff=False` are rejected with **403** by default. No body leakage. | `tests/test_security.py::test_non_staff_rejected_for_every_endpoint`. |
| S-3 | The default access policy is exactly `user.is_authenticated and user.is_active and user.is_staff and admin_site.has_permission(request)`. The package never adds its own policy on top, and never falls back to a looser policy than what `AdminSite.has_permission()` returns. | `git grep -n is_admin_user django_admin_react/api/` matches `permissions.is_admin_user` and only that helper; every view calls it before any model access. |
| S-4 | The package **never** invents a `User`, `Group`, or `Permission` model. `INSTALLED_APPS` contributions are limited to the package's own `AppConfig` with no models. | `python -c "from django_admin_react.apps import DjangoAdminReactConfig; print(DjangoAdminReactConfig.name)"`; `git grep -n 'class.*Model' django_admin_react/` returns nothing in `models.py`. |
| S-5 | The package does **not** ship login views, password reset, OAuth, JWT issuance, or any auth flow. Auth is fully delegated to Django + the consumer's `AdminSite`. | `git grep -n 'login\|password\|jwt\|oauth\|token' django_admin_react/api/views/` returns no auth-flow code. |

### 4.2 Authorization (per-model, per-object)

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-6 | Every endpoint consults the matching `ModelAdmin.has_*_permission(request, obj=None)` **before** acting. No exceptions. | Each view in `django_admin_react/api/views/*.py` calls the right helper; covered by `tests/test_security.py::test_<endpoint>_calls_has_<op>_permission` (mock and assert call). |
| S-7 | For object-level operations (detail / update / delete), the `obj` is passed to `has_*_permission` so per-object overrides are respected. | Per-endpoint tests with a `ModelAdmin` whose `has_change_permission` returns False for specific objects; assert 403. |
| S-8 | A model whose `has_module_permission=False` for the request is **not listed** in `GET /api/v1/registry/`. A model whose `has_view_permission=False` is filtered from the registry's `models[]` array. | `tests/test_registry.py::test_registry_hides_models_without_module_permission` (already covered for view; add module). |
| S-9 | The `permissions: {view, add, change, delete}` block returned to the client mirrors `ModelAdmin.has_*_permission` exactly. Even if the client tries the forbidden action anyway, the server re-checks and returns 403. | `tests/test_security.py::test_permissions_payload_matches_modeladmin` + `tests/test_security.py::test_client_forged_permission_ignored`. |
| S-10 | The package **never** uses Django's content-type permissions directly (`user.has_perm('app.change_model')`) — always via `ModelAdmin.has_*_permission`. | `git grep -nE "user\.has_perm\(" django_admin_react/` returns nothing. |

### 4.3 Resource exposure (deny-by-default)

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-11 | Models **not registered** in the configured admin site return **404** for every endpoint. The 404 envelope leaks nothing about whether the model exists in the project at all. | `tests/test_security.py::test_unregistered_model_404_no_leakage`. |
| S-12 | Client-supplied `app_label` / `model_name` / field names are resolved by lookup into `admin.site._registry` only. No `import_string`, no `apps.get_model`, no `__import__` is called on client input. | `git grep -nE 'import_string\|get_model\(' django_admin_react/api/` — matches must be inside a `_registry.items()` loop or `get_admin_site()`. |
| S-13 | The package does **not** auto-register any model with the admin. The admin's `_registry` is read-only from the package's perspective. | `git grep -nE 'admin\.site\.register\|@admin\.register' django_admin_react/` returns nothing. |
| S-14 | `GET /api/v1/registry/` returns **only** apps that have ≥1 visible model for the request; empty apps are not listed. | `tests/test_registry.py::test_empty_apps_omitted`. |

### 4.4 Queryset protection

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-15 | List endpoints start from `ModelAdmin.get_queryset(request)`. `Model.objects.all()` / `Model.objects.filter()` calls do not appear anywhere under `django_admin_react/api/`. | `git grep -nE 'objects\.(all\|filter)\(' django_admin_react/api/` returns nothing. Enforced by a pre-commit grep hook (S-44). |
| S-16 | Search applies `ModelAdmin.get_search_results(request, qs, q)`. Results respect `may_have_duplicates`. | `tests/test_security.py::test_list_uses_get_search_results`. |
| S-17 | Detail endpoints fetch the object via `ModelAdmin.get_queryset(request).get(pk=...)`. An object outside the admin's queryset returns **404**, not 403. | `tests/test_security.py::test_detail_outside_queryset_returns_404`. |
| S-18 | List responses are clamped to `MAX_PAGE_SIZE` (default 200). Clients asking for more get silently clamped. | `tests/test_list.py::test_page_size_clamped_to_max`. |
| S-19 | Ordering tokens (`?ordering=`) are validated against `ModelAdmin.get_ordering(request)` (or `ModelAdmin.ordering`). Unknown tokens are dropped, not raised — never used to inject ORM fragments. | `tests/test_security.py::test_ordering_injection_dropped`. |

### 4.5 Form & write enforcement

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-20 | Create and update endpoints instantiate `ModelAdmin.get_form(request, obj=...)` and call `form.is_valid()`. No `setattr(obj, name, value)` from JSON exists in API view code. | `git grep -nE 'setattr\(.*request' django_admin_react/api/views/` returns nothing. |
| S-21 | PATCH builds form initial from the existing instance, merges the JSON body on top, then validates. Fields not declared by the form are **ignored** if absent from the payload, **rejected** with 400 if present. | `tests/test_update.py::test_patch_unknown_field_400` + `tests/test_update.py::test_patch_partial_merges_initial`. |
| S-22 | Fields in `ModelAdmin.get_readonly_fields(request, obj)` cannot be written. Attempting to set them via POST/PATCH returns **400**, and the database value is unchanged. | `tests/test_security.py::test_readonly_field_not_writable_400_and_unchanged`. |
| S-23 | Fields in `ModelAdmin.get_exclude(request, obj)` (or excluded from `get_fields`) cannot be written, **and are not included in responses**. | `tests/test_security.py::test_excluded_field_not_writable_and_not_serialized`. |
| S-24 | DELETE calls `ModelAdmin.delete_model(request, obj)`. `obj.delete()` does not appear in API view code. | `git grep -nE '\.delete\(\)' django_admin_react/api/views/delete.py` returns 0 matches in the view body. |
| S-25 | A non-existent `pk` returns **404** before any permission check that would leak existence. | `tests/test_security.py::test_nonexistent_pk_404_before_permission_leak`. |

### 4.6 Session, CSRF, cookies

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-26 | CSRF protection is enabled for every unsafe method (`POST`, `PUT`, `PATCH`, `DELETE`). No `@csrf_exempt` exists anywhere in the package. | `git grep -nE 'csrf_exempt\|ensure_csrf_cookie' django_admin_react/api/views/` returns 0 `csrf_exempt`. |
| S-27 | A request missing or with an invalid `X-CSRFToken` header on an unsafe method returns **403**. | `tests/test_security.py::test_csrf_missing_on_unsafe_method_403` (per endpoint). |
| S-28 | The SPA shell view (`SpaIndexView`) sets the CSRF cookie via Django's middleware (e.g., decorated with `ensure_csrf_cookie`). The cookie is `HttpOnly: false` (so JS can read it) but inherits `Secure` from Django settings. | `tests/test_views.py::test_spa_index_sets_csrf_cookie`. |
| S-29 | The package **never** writes to `request.session` directly, never invalidates the session, and never reads `SESSION_COOKIE_*` to override Django's settings. | `git grep -nE 'request\.session\|SESSION_COOKIE' django_admin_react/` returns 0. |
| S-30 | The package's API responses set `Cache-Control: no-store` for permission-denied responses, and never set permissive cache headers on responses that include user-specific data. | `tests/test_security.py::test_forbidden_response_no_store`. |

### 4.7 Serialization safety (defense in depth)

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-31 | The serializer's sensitive-field denylist matches at minimum: `password`, `secret`, `token`, `api_key`, `apikey`, `hash`, `private_key`, `session`, `nonce`, `salt`. Matching is case-insensitive and applies to substrings (e.g., `user_password_hash`). The denylist is applied **on top of** the admin form's `exclude` / `readonly`, never as a substitute. | Code: `django_admin_react/api/serializers.py` constant `SENSITIVE_FIELD_PATTERNS` plus `tests/test_security.py::test_sensitive_fields_never_serialized` parameterised over a synthetic model with `password`, `api_key`, etc. |
| S-32 | Unknown / unhandled field types fall back to `str(value)` — never `repr(value)`, never the raw object. | `tests/test_serializers.py::test_unknown_type_falls_back_to_str`. |
| S-33 | `ForeignKey` serialization returns `{ "id": ..., "label": str(obj) }`. The full related object is **not** serialized; no nested expansion. | `tests/test_serializers.py::test_fk_returns_id_and_label_only`. |
| S-34 | `ManyToMany` and unknown field types are returned as `type: "unsupported"` with a stable `value: null` shape, not omitted (so the UI can render a readonly stub). They are never editable in v1. | `tests/test_serializers.py::test_m2m_unsupported_stub`. |
| S-35 | A `DEBUG=True` Django setting on the consumer's side **does not** cause the serializer to leak more data (e.g., `Meta.private_fields`, internal `_state`, ORM lazy attributes). | `tests/test_security.py::test_debug_mode_does_not_leak_more`. |
| S-36 | The serializer does not call `model._meta.private_fields` for output. | `git grep -n 'private_fields' django_admin_react/api/serializers.py` returns 0 (we use the admin form's declared fields, not `_meta.fields`). |

### 4.8 Secret management & git hygiene

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-37 | No live secret, API token, password, PEM, private key, or `.env` content exists anywhere in the committed history of `origin/main`. Partial redactions (e.g., `ghp_…XYZ`) are also forbidden. | `gitleaks detect --source . --redact --no-banner` returns 0 high-severity findings. Re-run before every release. |
| S-38 | `.gitignore` blocks `.env`, `.env.*` (except `.env.example`), `*.pem`, `*.key`, `*.crt`, `secrets/`, `.secrets/`. | `cat .gitignore`; required entries present. |
| S-39 | A pre-commit hook (`.pre-commit-config.yaml`) runs `gitleaks` + a custom regex grep for `ghp_/gho_/ghs_/aws_secret_access_key/BEGIN.*PRIVATE KEY`. Devs are documented to enable it in `CONTRIBUTING.md` § "Pre-commit". | File exists; `pre-commit run --all-files` passes locally on a clean repo. |
| S-40 | Issue, PR, and forum templates explicitly warn against pasting secrets. | `.github/PULL_REQUEST_TEMPLATE.md` and `.github/ISSUE_TEMPLATE/*` contain the warning. |
| S-41 | If a secret leak is discovered (active or historical), a `forum/INCIDENT-*.md` is opened, the secret is rotated **first**, and history rewrite is gated by explicit human approval. | Procedure documented in [`SECURITY.md`](SECURITY.md) §5. |

### 4.9 Dependency security

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-42 | Every new third-party Python dependency in `pyproject.toml` has a corresponding entry in `docs/agents/decisions.md` explaining why it's needed and what alternative was rejected. | Diff review on every PR that touches `[tool.poetry.dependencies]` or dev deps. |
| S-43 | Every new third-party JS dependency in any `frontend/**/package.json` has a corresponding entry in `docs/agents/decisions.md`. | Same as S-42, on JS side. |
| S-44 | `poetry run pip-audit` returns 0 findings of severity ≥ HIGH at release time. | Run inside `scripts/audit-deps.sh` (planned); record in `PROGRESS.md` quality-gate table. |
| S-45 | `pnpm audit --prod` returns 0 findings of severity ≥ HIGH at release time. | Same as S-44 on JS side. |
| S-46 | `bandit -r django_admin_react` returns 0 findings of severity ≥ HIGH at release time. | Already wired in `scripts/lint.sh`. |
| S-47 | The package has **no runtime dependency** on `djangorestframework`, an OAuth/JWT library, or any auth framework other than Django itself. The only runtime dependency is Django 5.x. | `poetry export -f requirements.txt` shows Django + transitive only. |

### 4.10 PII and test fixtures

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-48 | No real names, real emails, real phone numbers, real addresses, real IBANs, real credit-card numbers, or any other PII appear in `tests/**` or `examples/**` fixtures. | Spot-check + `git grep -iE '@gmail\|@yahoo\|@hotmail\|@outlook' tests/ examples/` shows only obvious synthetic / Faker data. |
| S-49 | Example apps use clearly synthetic identifiers (Alice / Bob / Carol, `example.com`, `123-4567-8901-2345`-style fake card numbers tagged `# fake`). | Spot-check the example `models.py`, `admin.py`, and any seed-data files. |
| S-50 | The package **does not log** request bodies, response bodies, form input, cookies, headers containing `Authorization` / `Cookie` / `X-CSRFToken`. | `git grep -nE 'logger\.\|logging\.' django_admin_react/` — every match is inspected; none log raw request/response payloads. |

### 4.11 API hardening

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-51 | The package supports `HEAD` and `OPTIONS` correctly (no information leak), and returns **405** for `PUT` / `TRACE` / `CONNECT` on every endpoint. | `tests/test_security.py::test_unsupported_methods_return_405`. |
| S-52 | The API does not include a default open CORS configuration. If the consumer needs cross-origin access, they configure it via `django-cors-headers` themselves. The package's URLs do not register CORS middleware. | `git grep -nE 'CORS\|Access-Control' django_admin_react/` returns 0. |
| S-53 | The 500 error envelope **never** includes a stack trace, exception message, or request payload, even under `DEBUG=True`. | `tests/test_security.py::test_500_envelope_no_stack`. |
| S-54 | A debug / introspection endpoint (e.g., `/api/v1/__debug__/`) does **not** exist. | `git grep -nE '__debug__\|introspect\|inspect_routes' django_admin_react/` returns 0. |

### 4.12 Logging safety

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-55 | All package logs use a dedicated `django_admin_react` logger. Log messages do **not** include user PII, request bodies, cookies, headers with secrets, query strings with `?token=...`-shaped data, or full response bodies. | Manual review of every `logger.*(` call in `django_admin_react/`. |
| S-56 | Error logs include the path, status, and short reason — never the user's verbatim input if it could contain credentials. | Per-endpoint review when implementations land. |

### 4.13 Release & publishing hygiene

| # | Criterion | How to verify |
| - | --------- | ------------- |
| S-57 | PyPI publishing requires `POETRY_PYPI_TOKEN_PYPI` in env. `scripts/deploy.sh` refuses to run if the token is missing or empty. | `bash -c 'unset POETRY_PYPI_TOKEN_PYPI; ./scripts/deploy.sh'` exits non-zero with a clear error. |
| S-58 | The PyPI token is **never** echoed, stored in any file in the repo, or printed to any log. The `scripts/deploy.sh` code does not echo `$POETRY_PYPI_TOKEN_PYPI`. | Manual review of `scripts/deploy.sh`. |
| S-59 | A release tag is **never** pushed by an agent without explicit human approval. Tier 6 in [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md). | Confirm by audit-trail: `forum/AGENT-*-pr-*-audit.md` for any release PR shows a human approver. |
| S-60 | `pyproject.toml` version is not `0.0.0` at release time; an SBOM (CycloneDX or equivalent) is produced for each release. | `scripts/build.sh` + a small SBOM step (planned). |
| S-61 | Released wheels embed the pre-built React SPA, **not** sources. The wheel contains hashed `django_admin_react/static/admin_react/*` and `templates/admin_react/index.html`; it does **not** contain `frontend/`, `node_modules/`, or any source `.ts` / `.tsx`. | `unzip -l dist/*.whl` shows static + templates, not frontend source. |

### 4.14 Secure-default recommendations (consumer side)

The package documents the following recommended consumer settings in
`SECURITY.md` §"Recommended consumer settings". The package does
**not** override them — secure default is a contract, not silent
behavior.

| # | Recommendation | Why |
| - | -------------- | --- |
| S-62 | `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`. | Stops cookie leakage over HTTP. |
| S-63 | `SECURE_HSTS_SECONDS ≥ 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_HSTS_PRELOAD = True` (with caveats). | Forces HTTPS at the browser. |
| S-64 | `X_FRAME_OPTIONS = "DENY"`. | Clickjacking. |
| S-65 | `SECURE_CONTENT_TYPE_NOSNIFF = True`, `SECURE_BROWSER_XSS_FILTER = True`. | Content-type and legacy XSS protections. |
| S-66 | Recommended CSP snippet for `django-csp` or middleware in `docs/installation.md` once frontend lands; CSP does not break the bundled SPA. | Defense in depth; tracked at [QSEC-2026-05-25-03](docs/agents/security-expert/OPEN_QUESTIONS.md). |

### 4.15 Mandatory test matrix

The Merger may not merge a PR that adds or changes any API endpoint
unless `tests/test_security.py` covers, for that endpoint, **all** of:

- [ ] Anonymous → 403 (no body leakage).
- [ ] Authenticated non-staff → 403.
- [ ] Staff without per-model permission → 403.
- [ ] Staff with permission → 200/201/204 as appropriate.
- [ ] Unregistered model → 404.
- [ ] Non-existent pk → 404.
- [ ] CSRF missing on unsafe method → 403.
- [ ] Write to readonly / excluded field → 400, value unchanged.
- [ ] Sensitive-shaped field never appears in any response.
- [ ] `permissions` payload matches `ModelAdmin.has_*_permission`.

Per-endpoint additions (e.g., search delegation, ordering injection)
are listed alongside the test file when the endpoint lands.

### 4.16 Release-blocking issues

The Security role **blocks** a release if any of the following is
true, regardless of how green the rest of `ACCEPTANCE.md` looks:

- B-1 A live or partial secret is found in `origin/main` history.
- B-2 Any criterion S-1 through S-61 is ❌ or 🟡.
- B-3 `pip-audit` or `pnpm audit` reports severity ≥ HIGH.
- B-4 `bandit` reports severity ≥ HIGH inside `django_admin_react/`.
- B-5 `tests/test_security.py` is failing or `xfail`-ed without a
  linked GitHub issue + human approval.
- B-6 A new urls.py pattern is added that mounts content outside
  the configured admin site without re-checking authentication.
- B-7 An endpoint is added that does not pass through
  `ModelAdmin` permission / queryset / form gates.
- B-8 The denylist in §4.7 is weakened or `csrf_exempt` appears
  anywhere in the package.

### 4.17 Dependencies on other roles

- §4.6 S-28 depends on the Architect role wiring `SpaIndexView`
  with `ensure_csrf_cookie` (or equivalent) in PR #6.
- §4.7 S-31–S-36 depend on the Architect role implementing
  `django_admin_react/api/serializers.py` with the denylist in
  the same PR that introduces field serialization.
- §4.13 S-57–S-61 depend on the PM/UX role for the release
  documentation; the actual token and trigger remain human-only.

Cross-team handoffs are tracked in
[`docs/agents/handoff.md`](docs/agents/handoff.md) (entry H-2026-05-25-02
acknowledges this section is now populated).

---

## 5. Composite release gate

A release tag may only be pushed when **every applicable criterion**
in §2, §3, and §4 is ✅ for the milestone being released.

**v1 (`0.1.0`) release gate** — composite checklist:

- [ ] §2.1 P-1 through P-5 ✅
- [ ] §2.2 D-1 through D-5 ✅
- [ ] §2.3 O-1 through O-5 ✅
- [ ] §2.4 R-1 through R-5 ✅
- [ ] §2.5 A-1 through A-7 ✅
- [ ] §2.6 Doc-1 through Doc-5 ✅
- [ ] §2.7 N-1 through N-5 ✅
- [ ] §2.8 V-1 through V-5 ✅
- [ ] §2.9 E-1 through E-5 ✅
- [ ] §3 ✅ (entire section; Architect role)
- [ ] §4 ✅ (entire section; Security role)
- [ ] `PROGRESS.md` quality-gates table all-green
- [ ] Repo owner has provided the PyPI token and explicit go-ahead

If any line is not ✅, the release is **not v1**. The next release
candidate is `0.1.0rcN` or the milestone is renamed.

---

## 6. Cross-references

- [`PRODUCT_VISION.md`](PRODUCT_VISION.md) — the why.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the system contract.
- [`SECURITY.md`](SECURITY.md) — non-negotiable security rules.
- [`PLAN.md`](PLAN.md) — engineering PR sequence.
- [`PROGRESS.md`](PROGRESS.md) — current status board.
- [`docs/agents/decisions.md`](docs/agents/decisions.md) — accepted
  decisions (PM-tagged entries are appended here when this file
  changes materially).
- [`docs/agents/open-questions.md`](docs/agents/open-questions.md) —
  open product questions.
