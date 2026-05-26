# Roadmap

Owner: `claude-pm-ux-opus47` (Product / UX).
Last reviewed: 2026-05-25.

> This is the **user-facing** roadmap — what we promise to ship and
> when. For the engineering PR sequence see [`PLAN.md`](PLAN.md). For
> the acceptance bar each release must clear see
> [`ACCEPTANCE.md`](ACCEPTANCE.md).

Tags:

- 🟢 Confirmed for the milestone.
- 🟡 Strong intent; final scope decided as we approach the milestone.
- 🔵 Stretch; ships only if the milestone is otherwise complete.
- ❌ Explicitly **not** in this milestone (anti-roadmap).

---

## v0.1 — "Plug it in and it works"

Goal: a Django dev can install the package, point a URL at it, and
get a responsive React admin for their existing `ModelAdmin`
classes — without touching any frontend code.

Target: every criterion in [`ACCEPTANCE.md`](ACCEPTANCE.md) §2.1 –
§2.9 reaches ✅. Releases on PyPI only when the human owner triggers
it with the API token (tier 6 in
[`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md)).

### What's in

- 🟢 **Registry** — list of apps and models the user may see.
- 🟢 **List view** — paginated, with the columns from
  `get_list_display`. Search box from `search_fields`. Ordering
  from `get_ordering`.
- 🟢 **Detail view** — render the model via `get_form(request, obj)`.
- 🟢 **Create / partial update / delete** — through
  `get_form()` + `save_model()` + `delete_model()`. No mass
  assignment.
- 🟢 **Permissions reflected from `ModelAdmin`** — add / change /
  delete buttons hide when the corresponding `has_*_permission` is
  `False`.
- 🟢 **Configurable URL mount** — package works at any prefix.
- 🟢 **Modern responsive UI** — Tailwind, light + dark mode, usable
  at 375 px wide.
- 🟢 **SPA navigation** — no full reloads; back/forward and refresh
  preserve state.
- 🟢 **`@dar/data` cache layer** — instant first paint from
  `localStorage`; debounced flush of edits to the API.
- 🟢 **Bundled wheel** — `pip install django-admin-react` ships the
  prebuilt SPA; no Node required on the consumer's machine.
- 🟢 **Demo Django apps** under `examples/` (fintech, library, blog,
  ecommerce, hr) — proof the package works against real-shaped
  `ModelAdmin` classes.
- 🟢 **Screenshots in README** — registry / list / detail / mobile /
  dark mode / login redirect.
- 🟡 **Lightweight choice filters** (`list_filter` entries that are
  `BooleanField` or fields with `choices`). Anything else
  silently ignored in v0.1, called out in docs.
  *(Depends on Architect handoff Q-PM-03.)*

### What's out (anti-roadmap for v0.1)

- ❌ Inlines (`InlineModelAdmin`).
- ❌ Custom admin actions and bulk actions.
- ❌ Autocomplete / `raw_id_fields`.
- ❌ Custom widgets beyond the v1 type vocabulary
  ([`docs/api-contract.md`](docs/api-contract.md) §4).
- ❌ ManyToMany editing (read-only stub).
- ❌ A React-side plugin / extension API.
- ❌ Server-rendered HTML fallback.
- ❌ Multi-`AdminSite` support.
- ❌ Internationalisation beyond `LANGUAGE_CODE` defaults.
- ❌ Command palette (`cmd+k`).

---

## v0.2 — "Polish and parity"

Goal: close the most obvious "you don't have feature X from
`django.contrib.admin`" gaps without breaking v0.1.

### What's in

- 🟡 **Inlines** (`InlineModelAdmin`, `TabularInline`,
  `StackedInline`). One level of nesting in v0.2; deeper nesting is
  a stretch.
- 🟡 **Custom admin actions** — exposed via a small whitelist
  mechanism on the backend (no React extensibility yet).
- 🟡 **Bulk actions** (delete-selected at minimum, plus actions
  exposed by §above).
- 🟡 **`list_filter` UI** for common filter types
  (`AllValuesFieldListFilter`, choice filters, `BooleanFieldListFilter`).
- 🟡 **Date hierarchy** UI.
- 🟢 **Dark-mode polish** — designer pass; tighten accent contrast
  per real screenshots.
- 🟢 **Keyboard shortcuts** — `?` to show shortcut help.
- 🔵 **Command palette** (`cmd+k`) — navigate models; search inside
  models is v0.3.

### What's out

- ❌ React-side extension API.
- ❌ Per-user UI customisation (column reorder, saved views).

---

## v0.3 — "Power user"

Goal: turn the SPA into the admin a power user picks over the HTML
admin.

### What's in

- 🟡 **Autocomplete** fields (`autocomplete_fields`).
- 🟡 **`raw_id_fields`** UI.
- 🟡 **ManyToMany editing**.
- 🟡 **Saved views** — column order, page size, search query
  preserved per user.
- 🟡 **CSV / JSON export** of the current list view.
- 🔵 **Custom widgets** via a closed widget registry on the backend
  (still no client-side React extensibility).

### What's out

- ❌ React-side plugin API (still deferred until a real consumer
  needs it).

---

## v1.0 — "Stable contract"

Goal: lock the public surface. Tag `1.0.0`. Promise SemVer.

### What's in

- 🟢 **API v1 frozen.** Breaking changes go to `/api/v2/`.
- 🟢 **Settings keys frozen.** Adding a key after v1.0 is a minor
  bump; renaming or removing is a major.
- 🟢 **Design system tokens frozen.** Adding tokens is minor;
  changing existing token names or values is a major.
- 🟢 **Migration guide** from `0.x` (if any breakages happened).
- 🟢 **Long-term Django version table** — explicit support for
  Django 5.x and (verified) Django 6 by this point.

---

## Maybe-later (no commitment)

Things we have considered and **not** scheduled. If you want one of
these, open an issue with concrete use cases.

- **React-side extension API.** Only if a meaningful community
  builds plugins for the HTML admin and a clear shape emerges. Until
  then, extension happens on the Django side.
- **GraphQL API.** REST is fine for this surface; GraphQL is more
  complexity than benefit.
- **WebSocket live updates.** No real-time admin pattern is
  consistent enough across consumers to ship safely.
- **Embedded charts / dashboards.** Admins are for editing data,
  not for visualising it. Use a real BI tool.
- **Multi-tenant admin** (one SPA, many tenants). Out of scope —
  multi-tenancy is a Django app problem, not an admin problem.
- **AI features.** No.

---

## How this roadmap is maintained

- The PM/UX role owns this file.
- Every milestone-level decision is reflected here and in
  [`docs/agents/product-manager/DECISIONS.md`](docs/agents/product-manager/DECISIONS.md).
- Engineering scope sequencing for the **current** milestone lives
  in [`PLAN.md`](PLAN.md). When the two disagree, this file is
  product-authoritative and `PLAN.md` is engineering-authoritative;
  both are updated in the same PR.
- A milestone is **shipped** when [`ACCEPTANCE.md`](ACCEPTANCE.md) §5
  is fully green for that milestone and the human owner has
  authorised the release.

---

## Cross-references

- [`PRODUCT_VISION.md`](PRODUCT_VISION.md) — the why.
- [`ACCEPTANCE.md`](ACCEPTANCE.md) — the bar.
- [`PLAN.md`](PLAN.md) — engineering PR sequence.
- [`PROGRESS.md`](PROGRESS.md) — live status board.
- [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) — what "modern" looks like.
- [`ONBOARDING.md`](ONBOARDING.md) — how a dev starts.
