# Changelog

All notable changes to **django-admin-react** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(pre-1.0: expect breaking changes between `0.x` alphas — pin tightly).

Each released version also has a matching
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases)
(linked per section) and a [PyPI](https://pypi.org/project/django-admin-react/)
artifact. Keep the `[Unreleased]` section updated as PRs land; roll it into a
version section at release.

## [Unreleased]

### Security
- Route M2M / related saves through `ModelAdmin.save_related()` instead of a
  bare `form.save_m2m()`, so a consumer's override is honoured on every write
  (create / update / bulk) — Rule 1 (#402).
- DB `IntegrityError` the form didn't catch now returns a clean **409**
  (generic message — no driver/schema detail leaked), not an uncaught 500
  (#404).
- Over-limit multipart uploads return the canonical **400** JSON envelope
  rather than Django's default 400 page (#448).
- Restrict bulk-PATCH writes to `list_editable` fields — the bulk surface
  can't widen the editable set beyond the changelist (#401).
- Gate the inline change-link on the child's per-user `has_view_permission`,
  not just registration — least disclosure (#301).
- File uploads (#241) are validated server-side: filenames sanitised by
  storage (no path traversal), a file posted to a readonly/excluded/unknown
  field is rejected, and `PRIMARY_COLOR` (#437) is strict-hex-validated before
  it reaches the SPA `<style>` block (no CSS injection).

### Added
- **FileField / ImageField multipart upload** — create + update write path
  with `ClearableFileInput` clear-semantics (empty input keeps the file;
  `<field>-clear` removes it) (#241).
- Save inline children **atomically with the parent** on create (#403).
- `date_hierarchy`-independent **"Show all N"** pagination
  (`list_max_show_all`) (#394).
- `show_full_result_count` parity — `full_count` on the list response (#311).
- Inline `show_change_link` — per-row link to the child's change page (#384).
- Object-level change-page actions surfaced on detail (#236, backend).
- Themable accent color via `DJANGO_ADMIN_REACT["PRIMARY_COLOR"]` (#437).
- `prepopulated_fields` — slugify a field from sources while typing (#245).
- SimpleListFilter applied-default reflected as `selected` (#283).
- Collapsible detail sections (#359) and sidebar app-group sections (#227),
  persisted per model; reusable Breadcrumb (#355); drag-to-resize table
  columns (#425); pinned pk column (#360); `@dar/customization` surface (#423).

### Changed
- Enforce `mypy` on the package in the lint sweep so it can't silently
  regress (#312).
- Edit mode shows only editable fields and hides empty sections (#426);
  preserve fieldset multi-field (tuple) rows (#382); skeletons on
  detail / create / home loads (#375).

### Fixed
- Surface non-field (`clean()` / `__all__`) validation errors (#381).
- Edit stacked inlines as vertical blocks, not a table (#387).
- Keyboard `focus-visible` rings on Button + standardised focus (#434);
  dark-mode coverage for amber banners + static backgrounds (#433);
  unify border color + sort-caret on header hover (#429).
- Drop redundant, self-evident UI chrome (#410).

## [0.2.0a5] — 2026-05-27
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.2.0a5)

### Security
- Gate the ForeignKey/M2M `to` navigation link on the **target** model's
  per-user `has_view_permission`, not just registry membership — least
  disclosure, extends the #89 guard (#301).
- Ship a concrete recommended **Content-Security-Policy** for the SPA shell in
  `SECURITY.md` §9 (`script-src 'self'`; Report-Only rollout guidance) (QSEC-03).
- Enforce the `@dar/api` import boundary + re-clean `mypy` across the API (#312, #319).
- Codify the `bandit` security-lint scope in `pyproject [tool.bandit]` (#343).
- Purge the client cache (localStorage + service-worker) on logout, so cached
  records can't survive sign-out on a shared machine (#363).
- Drop source maps from the published wheel — no `.js.map` ships to PyPI,
  shrinking the artifact and removing source-reconstruction exposure (#362).
- Lock per-action `allowed_permissions` enforcement with a regression test:
  a delete-gated action is unreachable (404) for a user without delete
  permission (#361, #302).

### Added
- React **password set/change** endpoint — `UserAdmin` parity, delegates to the
  admin's own password form, never echoes the credential (#252).
- **ManyToMany write** widget (checkbox multi-select) (#240).
- Collapsible fieldsets + fieldset `description` (Django change-form parity) (#325).
- "View on site" link on detail (`ModelAdmin.view_on_site` parity) (#334).
- Django **save-flow buttons** — Save / continue / add another / save as new (#154).
- **`date_hierarchy`** drill-down strip on the list view (#349).
- **Logout** from the Settings modal (#363).
- Read-mode display parity: choice labels, file download links, boolean icons (#314).
- Toast notifications for save / create / delete / bulk actions (#289).
- Home page grouped by app (matches Django's index) (#321).
- Delete-confirmation **cascade preview** in the SPA (#153).
- Unsaved-changes guard on edit/create forms (#290); modal focus trap +
  restore + `aria-labelledby` (#292); list empty-state with an "Add" CTA (#293).
- **Frontend test runner** (vitest + Testing Library) and starter suites for
  `@dar/data` (`format`, `useSwrCache`), `FieldValueView`, and mutations (#310).
- **Frontend lint gate** — ESLint v9 flat config + typescript-eslint +
  react-hooks + Stylelint (#346).

### Changed
- Apply `ModelAdmin.list_select_related` to avoid an N+1 on FK list columns (#320).
- Loading skeletons on list refetch — filter / search / sort / page (#357).
- Generic search placeholder + plain empty-state copy (#358).
- Reconciled stale docs: `ARCHITECTURE.md` §8, `README`/`CONTRIBUTING`, and the
  `docs/` index now match shipped reality (#257, #326).
- Raised test coverage to the `ACCEPTANCE.md` §3.5 T-2 gate: `permissions.py` +
  `serializers.py` at 100%, all `views/*.py` ≥ 95% (#271, #274, #288).
- Run the frontend eslint + stylelint gate inside `scripts/lint.sh` so the
  pre-merge sweep actually enforces it (#351).

### Fixed
- Several dark-mode contrast/border issues across banners, forms, and the
  sidebar (#277, #295, #317, #323, #336).
- A readonly callable that raises now degrades to `null` instead of 500ing the
  detail endpoint (#276).

## [0.2.0a4] — 2026-05-26
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.2.0a4)

### Added
- SPA **inline editor** — add / edit / delete child rows (#223).
- PWA: install affordance in the sidebar + service-worker registration (#86).
- Navigable ForeignKey cells in the list (#217) and FK links in detail (#215).
- List **column customizer** (Columns modal) (#214).

## [0.2.0a3] — 2026-05-26
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.2.0a3)

### Added
- **React login form** end-to-end + create form completing CRUD (#167, #199).
- PWA backend: manifest + service-worker serving (#86).
- Autocomplete FK typeahead widget (#207); `date_hierarchy` drill-down strip (#205).
- Click-to-sort list columns via URL ordering (#195); shared `@dar/ui` Modal +
  styled bulk-action confirm (#206).

### Security
- Origin check on the service-worker `message` handler
  (CodeQL `js/missing-origin-check`) (#208).

## [0.2.0a2] — 2026-05-26
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.2.0a2)

### Added
- Detail **write surface** (edit + delete) (#192) and the **inline formset
  write** path (#54 write half) (#183).
- List toolbar + inline rendering (#189); `list_filter` sidebar (#175); mobile
  slide-in sidebar drawer (#85).
- **CodeQL** workflow + pre-commit in the lint sweep (#144).

### Security
- Cleared 4 real CodeQL alerts (2 HIGH, 2 MEDIUM) (#191).

## [0.2.0a1] — 2026-05-26
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.2.0a1)

### Added
- Honor `AdminSite.get_app_list` — surface consumer groupings (#138).
- Structured range-field envelope on read (#141); `BRAND_TITLE` / `BRAND_LOGO_URL` (#148).

### Security
- Fix a ManyToMany silent-wipe on a broken descriptor during PATCH
  (S-CRIT-1) (#119); switch vulnerability reporting to GitHub Security
  Advisories (#127).

## [0.1.0a2] — 2026-05-26
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.1.0a2)

### Added
- `date_hierarchy` drill-down on the list endpoint (#80).
- Extended field-type vocabulary + `register_field_type` hook (#90).
- Session-expiry contract (distinct error code on a stale session) (#95).
- Django 6 support (#75).

## [0.1.0a1] — 2026-05-26
[GitHub Release](https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.1.0a1)

### Added
- Initial alpha: the REST API over `ModelAdmin` — registry / list / detail /
  create / update / delete. Staff-only + CSRF always on; queryset starts from
  `ModelAdmin.get_queryset`; writes through `ModelAdmin.get_form`; conservative
  serializer + sensitive-name denylist. Ships the pre-built React bundle.

[Unreleased]: https://github.com/MartinCastroAlvarez/django-admin-react/compare/v0.2.0a5...HEAD
[0.2.0a5]: https://github.com/MartinCastroAlvarez/django-admin-react/compare/v0.2.0a4...v0.2.0a5
[0.2.0a4]: https://github.com/MartinCastroAlvarez/django-admin-react/compare/v0.2.0a3...v0.2.0a4
[0.2.0a3]: https://github.com/MartinCastroAlvarez/django-admin-react/compare/v0.2.0a2...v0.2.0a3
[0.2.0a2]: https://github.com/MartinCastroAlvarez/django-admin-react/compare/v0.2.0a1...v0.2.0a2
[0.2.0a1]: https://github.com/MartinCastroAlvarez/django-admin-react/compare/v0.1.0a2...v0.2.0a1
[0.1.0a2]: https://github.com/MartinCastroAlvarez/django-admin-react/compare/v0.1.0a1...v0.1.0a2
[0.1.0a1]: https://github.com/MartinCastroAlvarez/django-admin-react/releases/tag/v0.1.0a1
