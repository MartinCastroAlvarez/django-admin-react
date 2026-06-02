# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.13.0] — 2026-06-03

### Changed
- **The detail page now opens in the read-only DETAILS view by default,
  including on the Django-admin `/<app>/<model>/<pk>/change/` URL alias
  (#682).** Previously `/change/` forced edit mode, so a shared record link
  dropped recipients into an editable form (with empty inline "add" rows) —
  one stray keystroke from an accidental save. Now both `/<pk>` and
  `/<pk>/change/` render the same read-back view (FK/M2M as linked labels,
  choices as their display label, inlines as read-only tables); the toolbar
  **Edit** button flips the page into edit mode in place (no URL change), and
  `?edit=1` still deep-links straight to edit (and lands the "Save and
  continue editing" round-trip there). View-only users never see the Edit
  button. The add form (`/add/`) is unaffected — it still opens ready to fill
  in. No backend / form-spec contract change.

## [1.12.0] — 2026-06-02

### Added
- **Custom `change_form_template` admins now render INSIDE the SPA shell via a
  server-rendered html-fragment — no iframe (#679).** The form-spec endpoint
  (rest-api 1.7.0+, #75) renders a custom-template admin server-side, strips
  the admin chrome, and returns `{renderer: "html-fragment", html, csrf_token,
  submit_url, method, messages}`. The SPA injects that HTML into the content
  area while the breadcrumb / sidebar / title / toolbar stay React-rendered.
  Inline `<script>` / `<style>` the integrator's template emits **execute /
  apply after injection**: `dangerouslySetInnerHTML` leaves parsed `<script>`
  elements inert, so the new `HtmlFragment` component clones each into a fresh
  `<script>` and re-inserts it (the dual-listbox JS only runs because of this).
  The injected `<form>` POSTs via `fetch(…, {credentials: "include", headers:
  {"X-CSRFToken": …}})` to the round-trip route; a returned `html-fragment`
  re-injects in place (validation errors, no SPA route change), a
  `{renderer: "redirect", to}` triggers an SPA `navigate(to)` (never a
  `window.location` reload), and any Django `messages` surface as toasts.
  The backend HTML is **trusted** — it is the integrator's own admin template,
  rendered behind the same auth as `/admin/` over the same-origin API — so the
  custom JS/CSS is injected verbatim, deliberately not sanitised (see the
  `HtmlFragment.tsx` trust-boundary note). ModelAdmins that use only documented
  hooks (`form` / `fieldsets` / `formfield_overrides` / `get_form`) are
  unaffected — they keep rendering via the JSON field-map path. The
  `examples/jobs` `?run_custom=1` dual-listbox fixture exercises the full path
  (form-spec → POST → validation re-render → redirect) end-to-end against the
  example backend.

### Removed
- **The `legacy-iframe` renderer and its iframe fallback are gone (#679).**
  No iframe element is ever rendered for a custom-template form again. This
  drops `LegacyIframe` (and the #673 "detect framing refusal → open-in-new-tab"
  workaround) and the `safeLegacyUrl` same-origin validation that only guarded
  the iframe `src`. Custom-template admins now render in-shell via the
  html-fragment renderer above — no `X-Frame-Options`, `SameSite=None; Secure`,
  or cross-origin cookie bridge required. The contract type drops
  `LegacyIframeResponse` / `renderer: "legacy-iframe"` and adds
  `HtmlFragmentResponse` (`renderer: "html-fragment"`) + `RedirectResponse`
  (`renderer: "redirect"`).

### Changed
- **`django-admin-rest-api` floor raised to `^1.7.0` (#679).** 1.7.0 ships the
  html-fragment form-spec renderer (`renderer: "html-fragment"`) plus the POST
  round-trip route the in-shell custom form submits to. The SPA still degrades
  gracefully to the JSON form-spec / detail-driven form on an older backend.

## [1.11.2] — 2026-06-02

### Fixed
- **Detail-page toolbar: History / Refresh / Edit / Delete now flow inline
  with the custom `@admin.action` buttons (#677).** They were grouped in a
  right-aligned `ml-auto` cluster (#658/#672), which read as a *second*
  toolbar in its own column and could float disconnected from its row on
  narrow viewports. The toolbar is now a single `flex-wrap` container with no
  `ml-auto` spacer: every built-in is a plain button in the same flow,
  wrapping naturally wherever it falls, in DOM order `[History] [...custom
  actions] [Refresh] [Edit] [Delete]`. Destructive emphasis on Delete remains
  the button's own variant, not its position. Regression tests updated to pin
  the no-`ml-auto` inline contract.

## [1.11.1] — 2026-06-02

### Fixed
- **Detail-page toolbar no longer pushes the title off-screen (#672).** The
  header already stacked breadcrumb / title / toolbar as three full-width rows
  (#658/#674), but a `ModelAdmin` with 8+ actions still overflowed
  horizontally and dragged the H1 + breadcrumb out of view. Root cause was the
  flexbox `min-width: auto` default on the content column: `<main>` is a flex
  item, so it refused to shrink below the intrinsic width of the widest
  toolbar and `flex-1` blew it past the viewport — no header re-stacking could
  help. `<main>` now carries `min-w-0` so it shrinks to the viewport and the
  toolbar's `flex-wrap` actually reflows the buttons; the toolbar row is
  `w-full min-w-0`, long action labels wrap inside their button
  (`whitespace-normal break-words`) instead of forming a wide min-content box,
  and the Edit/Delete cluster stays right-aligned (`ml-auto`) on the last line
  regardless of how many custom actions exist. New `examples/many_actions`
  `PipelineAdmin` fixture (12 batch + 2 detail-only actions) plus
  `DetailPage.test.tsx` guards pin the wrapping behaviour.
- **Legacy-iframe shows a clear fallback instead of a broken-image icon
  (#673).** When the legacy admin refuses to be framed (Django's
  `XFrameOptionsMiddleware` sends `X-Frame-Options: DENY`, or a cross-origin
  `frame-ancestors` block), the browser painted its broken-image glyph and no
  `error` event fired. `LegacyIframe` now runs a `loading → loaded → refused`
  state machine — `onLoad` marks the frame loaded; a ~4s timeout with no
  `onLoad` marks it `refused` and swaps in an explicit "Embedding refused by
  the legacy admin — open in new tab" fallback (keeping the proven-working
  Open-in-new-tab button and the #665 same-origin validation + `sandbox`).
  README now documents the required backend headers
  (`X-Frame-Options: SAMEORIGIN` / removing `XFrameOptionsMiddleware`; for
  cross-origin, `Content-Security-Policy: frame-ancestors <spa-origin>` plus
  `SESSION_COOKIE_SAMESITE = "None"` + `SESSION_COOKIE_SECURE`), and the
  `examples/jobs` `?run_custom=1` variant exercises the path end-to-end.

## [1.11.0] — 2026-06-02

### Added
- **Faithful rendering for every form-spec `widget.kind` (#664).** The
  form-spec wire declares 23 `widget.kind` values; the change form previously
  mapped only 5 and let the rest silently fall back to the control implied by
  `FieldType` — so `hidden` rendered as a *visible, editable* input,
  `split-datetime` collapsed to one control, and the multi-selects / `file`
  had no faithful path. `adaptFormSpec` now maps **all 23** explicitly (an
  exhaustive `Record<WidgetKind, …>` so a new kind is a compile error), and
  `FieldInput` gained branches for `hidden` (real hidden input),
  `split-datetime` (date + time), `select-date` (date input),
  `checkbox-multiple` / `select-multiple` (checkbox bank / `<select multiple>`),
  `autocomplete` / `autocomplete-multiple`, and `file` (limited control + a
  legacy-admin note; upload itself still tracked by #241). Any future kind
  with no rich renderer maps to an explicit, operator-visible
  `unsupported_widget` tracked fallback — never a silent wrong control.
  `adaptFormSpec.test.ts` now asserts every enum member maps to something
  sensible.
- **System checks for misconfiguration (#667).** A new
  `django_admin_react/checks.py` registers a `manage.py check` validator that
  surfaces, with actionable hints: `django_admin_rest_api` missing from
  `INSTALLED_APPS` (Error), an unimportable `ADMIN_SITE` dotted path (Error),
  unknown `DJANGO_ADMIN_REACT` keys (Error, at startup instead of a lazy
  `ValueError`), an `API_URL_PREFIX` that requires the consumer to mount the
  REST API themselves (Warning), and a missing built SPA bundle / Vite
  manifest (Warning).

### Changed
- **`list_display_links` is now honoured (#666).** The changelist wire emits
  `list_display_links` (rest-api); the SPA links exactly the configured
  column(s) to the change page — and links *none* (rows inert) when the admin
  sets `list_display_links = None`. Previously the SPA hard-pinned the link to
  the first column. A pre-1.6.0 backend (no field on the wire) keeps the
  legacy first-column behaviour.
- **Raised the `django-admin-rest-api` floor to `^1.6.0` (#664).** 1.6.0 adds
  `prepopulated_fields` + autocomplete hints to the form-spec wire (already
  consumed for the add form via #245/#629; the autocomplete hint now drives
  the `autocomplete` widget kind).
- **README parity table corrected (#668).** `raw_id_fields`, `radio_fields`,
  and `filter_horizontal` / `filter_vertical` flip to ✅ (they ship today —
  pk-input + lookup, radio bank, and the `ShuttleSelect` two-pane widget).
  The stale "does NOT carry through" entries for those hooks were removed, and
  a new section documents the genuine gaps: `empty_value_display` (hard-coded
  `—`), custom `AdminSite.each_context` extra keys, and `list_select_related`.

### Security
- **Validated + sandboxed the legacy-admin iframe (#665).** `legacy_url` from
  the form-spec `legacy-iframe` fallback is now validated before it reaches
  the `<iframe src>` / `<a href>` sinks: only a same-origin `http(s)` URL is
  framed/linked; a `javascript:` / `data:` / `blob:` scheme or an off-origin
  target renders an inert error card instead (mirroring the
  `action-redirect.ts` discipline every other navigational sink in the SPA
  follows). The iframe now carries
  `sandbox="allow-forms allow-scripts allow-same-origin"` (defence in depth —
  drops `allow-top-navigation` / `allow-popups` / `allow-modals`).
  `SECURITY.md` §QSEC-03 gained `frame-src 'self'` and documents the
  X-Frame-Options ↔ legacy-iframe interaction.

### Performance
- **Route-level code-splitting + show-all row windowing (#670).** `LoginPage`
  and `CreatePage` are now `React.lazy`-loaded at the route boundary (out of
  the first-paint main chunk). The "Show all N" (`?all`) list path applies
  native row windowing (`content-visibility: auto`) so off-screen rows skip
  layout/paint while staying in the DOM for find-in-page / a11y.

### Fixed
- **i18n: routed untranslated strings through `t()` (#669).** `FieldInput`'s
  `Lookup ↗` / lookup aria-label, the `— select —` / `(none)` placeholders,
  and the time / array / range / FK placeholders, plus `App.tsx`'s "Page not
  found.", now go through the catalog; the new keys (and the #664 / #665
  operator notes) were added to the es / fr / pt catalogs.

## [1.10.1] — 2026-06-02

### Fixed
- **Restored the detail-page stacked-header layout (#658), which the #657
  module-split refactor silently reverted.** The header had regressed to the
  pre-#658 single-row layout where breadcrumb + title share a flex row with
  the action toolbar — collapsing long single-token titles (filenames,
  slugs, UUIDs) to one-word-per-line at full H1 size, and letting an 8+
  action toolbar push the title off-screen. The header is again three
  stacked full-width rows (breadcrumb / title with `overflow-wrap: anywhere`
  / toolbar with Edit·Delete pinned trailing-edge via `ml-auto`). Added a
  `DetailPage` test asserting the stacked layout so a future refactor can't
  revert it unnoticed.

## [1.10.0] — 2026-06-02

### Added
- **`examples/jobs` — custom-form / legacy-iframe fixture app.** A single
  `Job` model whose `ModelAdmin` exercises the request-driven custom-view +
  custom-template pattern using *only* documented Django hooks
  (`formfield_for_dbfield`, an admin `action`, a `change_view` branch, a
  hand-rolled dual-listbox template) — no SPA-specific API. Proves the two
  rendering paths end-to-end: Path A (`/admin-react/jobs/job/<pk>/change/`)
  renders the stock form-spec with the large-textarea `metadata` widget;
  Path B (`?run_custom=1`) returns `renderer: "legacy-iframe"` and the SPA
  embeds the legacy page in an iframe inside its own chrome. Backend tests
  cover both paths and the ordered POST contract (#659).

### Changed
- **Raised dependency floors for the cross-repo custom-form contract:**
  `django-admin-rest-api` → `^1.5.0` (broadened `legacy-iframe` detection
  for request-driven custom views, #59) and `django-admin-mcp-api` →
  `>=1.3.0,<2.0.0` (matching MCP release, #70). The SPA's `LegacyIframe`
  renderer (#659) already consumes the `legacy-iframe` discriminator.

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
