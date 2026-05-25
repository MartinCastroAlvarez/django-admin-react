# Plan

This file is the working plan for `django-admin-react`. It is updated every
time a meaningful architectural or sequencing decision changes. Keep it
authoritative — if reality diverges, fix this file in the same PR.

> Read order for a new agent: [`CLAUDE.md`](CLAUDE.md) →
> [`ARCHITECTURE.md`](ARCHITECTURE.md) → this file →
> [`docs/agents/decisions.md`](docs/agents/decisions.md).

---

## 1. v1 scope

In scope (must ship before we tag `0.1.0`):

- List registered admin models (per-user, filtered by `has_module_permission`
  and `has_view_permission`).
- List objects with admin's `get_queryset`, pagination, search via
  `get_search_results`, columns via `get_list_display`.
- Detail view.
- Create via `ModelAdmin.get_form()` + `save_model`.
- Update (PATCH partial) via the same form, merging initial data.
- Delete via `ModelAdmin.delete_model`.
- Permissions surfaced to the UI as booleans.
- Tailwind UI: list, detail, create, edit, delete confirmation, sign-in
  redirect to Django admin login.
- A `@dar/data` context layer that hydrates from `localStorage` for
  instant first paint, reconciles with React Query results, and debounces
  user-initiated mutations before dispatching to `@dar/api`. UI packages
  read **only** from `@dar/data`, never from `@dar/api` directly.
- Configurable URL mount.
- Demo apps: `examples/fintech`, `examples/library`, `examples/blog`.
- CI: pytest, ruff, mypy (best-effort), frontend lint + typecheck + build.

Out of scope for v1 (tracked in `docs/agents/open-questions.md` if not
fully decided):

- Inlines.
- Custom admin actions.
- Bulk actions.
- Custom widgets.
- Complex filters (date hierarchies, list_filter UIs beyond simple choices).
- Autocomplete / `raw_id_fields`.
- ManyToMany editing (read-only stub only in v1).
- A React-side extension/plugin API.
- Server-rendered/dynamic Tailwind config replacement at runtime.

---

## 2. PR sequence

PRs are intentionally small and reviewable. Each PR adds tests for the
behavior it introduces.

| #  | Branch                       | Scope                                                                                              | Tests required |
| -- | ---------------------------- | -------------------------------------------------------------------------------------------------- | -------------- |
| 1  | `pr/01-foundation`           | This PR. Docs (ARCHITECTURE, PLAN, SECURITY, CONTRIBUTING, CLAUDE), folder skeleton, LICENSE.       | n/a (docs)     |
| 2  | `pr/02-package-skeleton`     | `pyproject.toml` (Poetry), `django_admin_react/` Python skeleton, `apps.py`, empty `urls.py`, conf loader, CI workflow stub. | smoke import |
| 3  | `pr/03-registry-endpoint`    | `GET /api/v1/registry/` reads `admin.site._registry`, applies staff + module permissions.           | anon 403, non-staff 403, staff 200, unregistered hidden |
| 4  | `pr/04-list-detail`          | List + detail endpoints using `get_queryset`, `get_list_display`, `get_search_results`.            | search delegated, queryset delegated, fields filtered, perms enforced |
| 5  | `pr/05-write-endpoints`      | Create / partial update / delete using `get_form` + `save_model` + `delete_model`.                 | excluded fields blocked, readonly blocked, perms enforced, PATCH merges initial |
| 6  | `pr/06-frontend-shell`       | `frontend/` pnpm workspace, `@dar/ui`, `@dar/api`, `@dar/data`, `@dar/shell`, build pipeline, theming. Includes the eslint rule that forbids UI packages from importing `@dar/api`. | lint + typecheck + build pass |
| 7  | `pr/07-frontend-pages`       | `@dar/list`, `@dar/details`, `@dar/models`, wired exclusively through `@dar/data` providers. Tailwind theme. | component tests for happy path, debounce/localStorage round-trip |
| 8  | `pr/08-examples-and-polish`  | `examples/fintech`, `examples/library`, `examples/blog`, install docs, screenshots, release notes. | examples run, E2E smoke optional |

Subsequent (post-v1) PRs are not pre-numbered; they will be proposed
through `docs/agents/open-questions.md`.

---

## 3. Working agreements

1. **Branches are short-lived.** One PR per branch. No multi-feature
   branches.
2. **Main is protected.** Even the foundation PR (#1) goes through review.
   The only direct push to `main` is the empty initial commit that
   bootstraps the repository.
3. **Every PR updates docs.** If a PR changes architecture, it updates
   `ARCHITECTURE.md`. If it changes the plan, it updates this file.
4. **Every folder has a `README.md`.** Adding a folder without one is a
   PR-blocking comment.
5. **No secrets in commits.** Pre-commit checks must reject `.env`,
   tokens, keys.
6. **Poetry for Python; pnpm for JS.** No mixing.
7. **Tests precede or accompany the feature.** A PR adding behavior without
   tests will be rejected unless it is purely documentation/scaffolding.
8. **Ambiguous → document the assumption.** Add it to
   `docs/agents/open-questions.md` and pick the simpler path. Do not invent
   complex designs to hedge against unspecified requirements.
9. **Boring over clever.** Stable, readable code beats a small abstraction
   win.

---

## 4. Recorded assumptions (from the kickoff brief)

The original brief is broad. Where it left implementation choices open, I
recorded the assumption here so that future agents do not re-litigate:

- **`ADMIN_SITE` defaults to `django.contrib.admin.site`.** Consumers with a
  custom `AdminSite` set `DJANGO_ADMIN_REACT["ADMIN_SITE"]` to its dotted
  path. The package never enumerates multiple admin sites.
- **Authentication is delegated.** The package's only access policy is "must
  be active and staff" — and even that is configurable by letting the
  consumer's `AdminSite.has_permission` override it. We do **not** ship JWT,
  OAuth, or token auth.
- **Tailwind theming uses CSS variables + Tailwind config extension.** Full
  config replacement is documented as "fork your bundle"; we will not ship
  runtime config swapping in v1.
- **ManyToMany fields are read-only in v1.** Editing them well requires
  autocomplete; both are deferred.
- **PyPI publishing is gated.** The repo prepares packaging but never pushes
  to PyPI without explicit human approval and an API token supplied at
  release time. CI may publish to TestPyPI for verification only when an
  authorized maintainer triggers it.
- **Demo apps live under `examples/`.** Each example is a full Django
  project that depends on the package locally (via Poetry path dep) and
  mounts the React admin at `/admin-react/`.
- **Django version target.** Django 5.x is the primary target. Django 6
  support is documented as an explicit goal but tested only opportunistically
  in v1.

If you find one of these assumptions is wrong or no longer applies, update
this file in the same PR that breaks it.

---

## 5. Definition of done for v1

- A consumer can `pip install django-admin-react`, add it to
  `INSTALLED_APPS`, `include()` its urls, log in as a staff user, and
  browse/edit any model registered with their `AdminSite`.
- The same `ModelAdmin` choices control both the legacy `/admin/` UI and the
  React UI: changing `list_display`, `has_*_permission`, `exclude`,
  `readonly_fields`, `search_fields`, etc. on a `ModelAdmin` is immediately
  reflected in the React UI on the next request.
- All v1 endpoints have the test matrix from `CLAUDE.md` §"Test minimums".
- CI is green on PR.
- `README.md` documents install + mount + customization in under one
  screenful, linking deeper docs.
