# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.9.0] — 2026-06-01

### Added

- **Change-form parity via the rest-api form-spec endpoint (#659).** The
  change form is now driven by `GET <app>/<model>/<pk>/form-spec/`
  (django-admin-rest-api 1.4.0+, #59) instead of discovering fields
  client-side from the model serializer. The SPA now honours the
  **ModelAdmin layer**: request-aware `get_form(request, obj)` /
  `get_fieldsets(request, obj)` / `get_readonly_fields(request, obj)`,
  `formfield_overrides`, custom `Form` classes, and the admin relation
  widgets — resolved server-side and mapped through the closed
  `widget.kind` enum. The original change-form querystring is forwarded,
  so a `get_form` that swaps the `Form` on `?variant=…` renders the same
  fields the legacy `/admin/` does. When the backend can't render the
  form from JSON (a `change_form_template` override → `renderer:
  "legacy-iframe"`), the SPA embeds the legacy admin page in an iframe
  inside the SPA shell instead of silently dropping the customisation
  (closes part of #624). A spec-fetch failure (older backend) degrades
  gracefully to the previous detail-payload-driven form. New API client
  method `formSpec()` + `useFormSpec` hook; the existing `FieldInput`
  renders the adapted fields unchanged (one control set, no drift).

### Changed

- **Split DetailPage/ListPage into focused modules (no behavior change)
  (#657).** Extracted the inner components of `DetailPage.tsx`
  (`DetailValue`, `FieldsetSection`, `ObjectActionButton`, `EditForm`,
  `CustomViewsMenu`, `DeleteButton`, `CollapsedEmptyInline`,
  `InlineSection`) into one-per-file modules under
  `apps/web/src/pages/detail/`, and lifted `ListPage.tsx`'s `capitalize` /
  `emptyLabel` helpers into `apps/web/src/pages/list/helpers.ts`. The page
  components keep their original paths + named exports; runtime behavior,
  props, and rendered output are unchanged.
- **Python lint stack consolidated onto Ruff (#651, #652).** Removed Black,
  standalone isort, and flake8 entirely (their `[tool.*]` config, dev
  dependencies, pre-commit hooks, and `scripts/lint.sh` steps). Ruff now owns
  lint + format + import order (the `I` rules), with mypy + bandit alongside —
  resolving the three-formatter conflict (#452/#452-skew) and the Black 24-vs-26
  pin skew. The now-green Python lint gate (ruff check + ruff format --check +
  mypy + bandit) is wired into backend CI.
- **mypy tightened on the package (#655).** Enabled the `disallow_untyped_defs`
  and `warn_return_any` strict subset for `django_admin_react`; typed the
  `admin_site` view helpers as `AdminSite` (type-only import) instead of `Any`.
- **Frontend `@typescript-eslint/no-explicit-any` promoted from `off` to
  `error` (#656)** to lock in the existing zero-`any` state, and added `/**`
  JSDoc to the `Checkbox`, `Input`, `Spinner`, `EmptyState`, and
  `DateHierarchyBar` primitives.

### Removed

- **Dead `django_admin_react/audit.py` module (#654).** It was imported nowhere
  and had 0% coverage; the `LogEntry` access it duplicated belongs in the
  sibling `django-admin-rest-api`.

### Fixed

- **Dangling documentation references (#653).** Repointed or removed docstring /
  comment / pre-commit citations to docs that no longer exist (`docs/ux/pwa.md`,
  `pwa.md`, `theming.md`, `ACCEPTANCE.md`, `REVIEW_CHECKLIST.md`,
  `docs/threat-model.md`) so they target the surviving `ARCHITECTURE.md` /
  `SECURITY.md` sections. Added a fast doc-reference guard
  (`tests/test_doc_refs.py` + a pre-commit hook) that fails when a `*.md` file
  or `§N` section cited in source no longer exists.
- **Stale comments (#654).** Removed the misleading "Real implementation lands
  in PR #2" note on the shipped `_PackageSettings` dataclass and a dead
  `# noqa: ARG002` line in `views.py` that suppressed nothing.
