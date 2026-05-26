# Extensibility contract

Owner: PM/UX lane.
Status: draft. Architect + Security must co-sign before any
implementation PR opens (see
[`forum/UX-DIRECTIVE-extensibility-contract.md`](../../forum/UX-DIRECTIVE-extensibility-contract.md)).

This document defines **what consumers can customise** in
`django-admin-react` without forking the package, and **how** that
customisation flows from `ModelAdmin` to the SPA. It is a PM/UX
contract: it specifies the user-facing surface, not the
implementation. The architecture lives in
[`ARCHITECTURE.md`](../../ARCHITECTURE.md); the threat model lives in
[`SECURITY.md`](../../SECURITY.md).

---

## 0. Tension this document resolves

The repo owner stated:

> django-admin-react should be plug-and-play (minimal configuration
> needed such as adding to settings.py and then setting the url)
> but also can be extensible (for example, some users might want to
> customize the CSS, some users might want to add new actions to
> the admin which would be picked by the dropdown selector, some
> users might want to add custom reports in some detail pages,
> inlines should be supported but reusing the django admin inline
> definitions) — for adding custom HTML in some detail pages,
> please work hand in hand with the software architect and security
> expert to make it happen in a seamless way but also well
> architectured and secure.

The two halves are in tension:

- **Plug-and-play** wants zero config beyond `INSTALLED_APPS` +
  `include()` (existing `ACCEPTANCE.md` §2.1 P-1..P-5).
- **Extensible** wants additional knobs.

The contract: each knob has a **default-off, opt-in** path that
preserves plug-and-play for the 80 % consumer who needs nothing
beyond `ModelAdmin`, while exposing the 20 % consumer to the
extension surface declared here.

---

## 1. Extension surfaces — at a glance

| # | Surface                       | Source of truth                              | Opt-in path                                           | Default for the 80 % consumer |
| - | ----------------------------- | -------------------------------------------- | ----------------------------------------------------- | ---------------------------- |
| X-1 | CSS / theming               | A static CSS file in the consumer's project  | `DJANGO_ADMIN_REACT["theme_css"] = "path/to/theme.css"` | Default tokens; no extra files. |
| X-2 | Custom admin actions        | `ModelAdmin.actions` (Django's own contract) | Just define them on `ModelAdmin`.                     | No actions → no dropdown.    |
| X-3 | Bulk row selection          | The SPA list page (built-in)                 | Auto-enabled when any X-2 action exists.              | Hidden when X-2 is empty.    |
| X-4 | Inlines                     | `ModelAdmin.inlines` (Django's own contract) | Just define inline classes.                           | No inlines → no inline section. |
| X-5 | Custom detail blocks ("reports") | New `ModelAdmin.get_detail_blocks(request, obj)` hook | Return a list of typed block descriptors.        | Returns `[]` → no extra blocks. |
| X-6 | Custom HTML in detail blocks | A specific block type (`type: "html"`) under X-5 | Server returns sanitised HTML; SPA renders it.    | Not used unless X-5 returns it. |
| X-7 | Custom React components     | **Not supported in v1.** See §10.            | n/a                                                   | n/a                          |
| X-8 | List filters                | `ModelAdmin.list_filter` (Django's own contract) | Just define them on `ModelAdmin`.                  | No `list_filter` → no filter sidebar. |

Each row of this table has a section below. The shared invariant
across all of them:

> Extensibility never requires the consumer to touch React, build
> the SPA, or know `frontend/` exists.

This invariant maps to **D-3** in `ACCEPTANCE.md` §2.2.

---

## 2. X-1 — CSS / theming

### Goal

Consumer overrides colour, spacing accents, typography accents — at
*runtime*, no rebuild — by pointing at a CSS file.

### Contract

- New optional setting in
  [`conf.py`](../../django_admin_react/conf.py) DEFAULTS:

  ```python
  "theme_css": None,  # str | None — path resolvable by Django staticfiles
  ```

- When set, the package serves the CSS file at a known URL and
  injects a `<link rel="stylesheet">` *before* the bundled CSS so
  CSS variables in the consumer's file win the cascade.
- The consumer's file overrides CSS variables only — `--dar-accent`,
  `--dar-bg`, `--dar-radius-md`, etc. Full token list lives in
  [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §3.

### What we never do

- Run the consumer's CSS through a build step at runtime.
- Allow arbitrary `@import` of external stylesheets — same CSP rule
  the rest of the SPA obeys (no third-party origins).

### UX expectations

- Editing the CSS file and reloading the page applies the new
  theme. No restart of `runserver` required.
- A clearly-malformed CSS file does not crash the SPA — the SPA
  falls back to default tokens, no white screen.

### Acceptance

Maps to **E-5** in `ACCEPTANCE.md` §2.9, plus a new **E-5a** for
the runtime-no-rebuild behaviour.

---

## 3. X-2 — Custom admin actions

### Goal

The consumer's existing `ModelAdmin.actions` is the source of
truth. Adding an action to `ModelAdmin.actions` causes it to
appear in the SPA's action dropdown on the list page, **without
any frontend change**. The behaviour matches Django's HTML admin:
the user ticks rows, picks an action from a dropdown, hits "Go".

### Contract

- Backend exposes the action metadata in the list-page response
  (`GET /api/v1/<app>/<model>/`) under a new `actions` key:

  ```json
  {
    "actions": [
      {
        "name": "make_published",
        "label": "Mark selected as published",
        "description": "Publishes the chosen items.",
        "requires_confirmation": false
      }
    ]
  }
  ```

  Source: `ModelAdmin.get_actions(request)`. Permissions are
  applied server-side, exactly as in `django.contrib.admin`.

- Backend exposes an invocation endpoint:

  ```
  POST /api/v1/<app>/<model>/actions/<action_name>/
  Body: {"pks": [1, 7, 12]}
  ```

  Response is either `{"status": "ok", "summary": "3 items
  updated."}` or a Django messages payload — Architect to specify
  the exact shape.

### SPA UX

- Above the list table, when **at least one** action is enabled
  for the current user on the current model:
  - Render a checkbox column on the table.
  - Render the dropdown + "Go" button matching Django's HTML
    admin layout, but styled per `DESIGN_SYSTEM.md`.
  - The dropdown reads from `actions` in the list payload.
- When no actions are available, the entire action toolbar is
  hidden — the table shows no checkboxes, no dropdown.
- Confirmation flow: `requires_confirmation: true` actions
  trigger a Dialog with the count + action name; "Cancel" /
  "Run" buttons. The `delete_selected` built-in action is always
  `requires_confirmation: true`.
- Long-running actions: the "Go" button spins ([`states.md`](states.md)
  §1) until the request resolves. No skeleton — this is a
  button state.

### What we never do

- Trust a client-side action name we don't recognise. Server
  rejects with 400 if the requested action is not in
  `get_actions(request)`.
- Run an action the user lacks permission for. Server enforces
  before dispatching.

### Acceptance

New criteria **E-6 a/b/c** in `ACCEPTANCE.md` §2.9 (drafted
below in §11).

---

## 4. X-3 — Bulk row selection

Trivial follow-on of X-2. When the SPA renders the action
dropdown (X-2), the table grows a checkbox column. Master
checkbox in the header toggles all *visible* rows (one page,
not the whole queryset).

Selection state is **not persisted** across page changes — that
is the same trade-off Django's HTML admin makes. A future "select
across all pages" flow is v1.x.

---

## 5. X-4 — Inlines

### Goal

`ModelAdmin.inlines = [BookInline]` is the source of truth.
Reusing `InlineModelAdmin`, `TabularInline`, `StackedInline` —
the same classes the consumer already wrote for the HTML admin.
**No new Django-side definition step.**

### Contract (PM/UX requirements — Architect signed off on the wire shape)

- The detail response (`GET /api/v1/<app>/<model>/<pk>/`) MUST
  include an `inlines: [...]` array describing each inline's:
  - `name` (the inline's underscore-cased class name),
  - `related_model` (e.g. `library.book`),
  - `fk_field` (the parent-pointing FK),
  - `display_kind` (`"tabular"` | `"stacked"`),
  - `fields`, `readonly_fields`, `extra`, `max_num`,
  - `permissions` for the inline's model (add / change / delete
    booleans, computed via `InlineModelAdmin.has_*_permission`),
  - and an embedded `rows` payload (filtered server-side by
    `inline.get_queryset(request).filter(parent_fk=parent)`).
  - **Permission leak guard (Security ask):** `inlines: [...]` MUST
    NOT ship metadata for related models the user has no `view`
    permission for. Filter the array server-side before
    serialising.

- **Atomic save** (Architect Q-EXT-05 answer): a single
  `PATCH /api/v1/<app>/<model>/<pk>/` carries inline edits via a
  new optional top-level body field:

  ```json
  {
    "title": "New title",
    "inlines": {
      "book_inline": {
        "rows": [
          {"id": 1, "title": "Edited"},
          {"id": null, "title": "Added"},
          {"id": 3, "_delete": true}
        ]
      }
    }
  }
  ```

  Server wraps the parent form save + every inline formset save in
  one `transaction.atomic()`. Validates everything first; if any
  validation fails, returns a per-row error envelope shaped like
  Django formset errors and rolls back. **No per-inline endpoint**
  and no transaction marker — single round-trip, fits cleanly
  with `@dar/data`'s debounce, matches Django's own admin POST
  shape.

### SPA UX

- After the parent form, render each inline as a section card
  ([`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §6 Layout — `Card`):
  - `display_kind: "tabular"` → a table with one row per child
    object; "Add row" button at the bottom (if
    `has_add_permission`); per-row delete (×) if
    `has_delete_permission`.
  - `display_kind: "stacked"` → each child rendered as a
    collapsed-by-default expandable subform.
- Validation errors on a child surface on that child's row /
  card, not on the parent.
- Optimistic UX rules from [`states.md`](states.md) §4 apply
  to inline edits.

### What we never do

- Build a parallel inline definition system in JavaScript.
- Render `inlines` whose related model is not registered with
  the AdminSite (we 404 / hide it).
- Allow editing child objects the user has no permission for —
  the SPA must hide the controls; the server must reject if
  the SPA misbehaves.

### Acceptance

New criteria **E-7 a/b/c** in `ACCEPTANCE.md` §2.9.

---

## 6. X-5 — Custom detail blocks ("reports")

### Goal

A `ModelAdmin` can return one or more "blocks" to render on the
detail page beyond the form and inlines — a chart, a stats card,
a related-data table — without any frontend code change.

### Contract (PM/UX requirements)

- New optional hook on `ModelAdmin`:

  ```python
  def get_detail_blocks(self, request, obj):
      return [
          {
              "title": "Recent transactions",
              "placement": "after_form",   # before_form | after_form | sidebar
              "type": "table",             # see §6.1
              "payload": { ... typed ... },
          },
      ]
  ```

  Default implementation returns `[]`.

- The detail endpoint (`GET /api/v1/<app>/<model>/<pk>/`)
  serialises the result under `detail_blocks: [...]`.

- **Per-block isolation (Architect ask, Security amplified).** Each
  block's server-side computation runs inside its own
  `try/except`. A failing block emits an `ErrorState` block in the
  same slot; sibling blocks render normally. Never 500 the page
  because one block raised.

- **Caching is consumer-managed** (Architect Q-EXT-06 answer). The
  package ships no DAR-side cache contract in v0.1. Consumers who
  want to memoize an expensive `get_detail_blocks` call use
  `django.core.cache` directly — they own both the cache key and
  the invalidation policy because they own the data the block
  reads. The contract is silent on cache headers.

### 6.1 Allowed block types (closed set in v0.1)

| `type`         | Payload shape                                                       | Renders as                                          |
| -------------- | ------------------------------------------------------------------- | --------------------------------------------------- |
| `"stats"`      | `{items: [{label, value, hint?}]}`                                 | Stat cards row.                                     |
| `"table"`      | `{columns: [{key, label}], rows: [{key: value}]}`                  | Read-only `Table` primitive.                        |
| `"description_list"` | `{items: [{label, value}]}`                                  | `<dl>` styled per design tokens.                    |
| `"markdown"`   | `{markdown: "string"}`                                              | Server renders markdown → runs through **the same `nh3` sanitiser** as `html` (we ship one sanitiser pipeline, not two). |
| `"html"`       | `{html: "<sanitised string>", sanitiser_version: "<n.n.n>", sanitiser_profile: "<name>"}` | See §7 below. Carries the sanitiser version + profile in the envelope. |

Block types are a closed enum in v0.1. New types require a
`docs/agents/decisions.md` entry and an Architect + Security
review.

### 6.2 Shipped example block

To prove X-5 without showcasing the escape-hatch type, exactly one
example block ships with the package (per Security Q-EXT-08):

> An "Account audit summary" block on `Account` detail in
> `examples/fintech/`, returning a `type: "stats"` block:
>
> ```json
> {
>   "title": "Account audit summary",
>   "placement": "after_form",
>   "type": "stats",
>   "payload": {
>     "items": [
>       {"label": "Open transactions (90 d)", "value": 12},
>       {"label": "Last login", "value": "2026-05-25T08:13:00Z"},
>       {"label": "Failed-login count (7 d)", "value": 0}
>     ]
>   }
> }
> ```
>
> Why this one: scalar values only, no HTML, computed over
> `ModelAdmin.get_queryset(request)`, plausibly useful for a real
> consumer.

We deliberately do **not** ship an `html` block example. The
contract says "the `html` type is the escape hatch, not the
default"; the example apps back that up by simply not using it.

### SPA UX

- Blocks render in declaration order, per their `placement` slot.
- A `placement: "sidebar"` block on mobile collapses below the
  form.
- A failed block (server returned an error for it) renders an
  `ErrorState` primitive scoped to that block — the rest of the
  page keeps working.
- Blocks respect the page's loading rules
  ([`states.md`](states.md) §1) — they have their own skeleton
  on first paint.

### What we never do

- Allow a block type the SPA doesn't know — unrecognised `type`
  is silently dropped client-side and logged as a warning.
- Trust block payloads to be safe HTML by default. See §7.

### Acceptance

New criteria **E-8 a/b/c** in `ACCEPTANCE.md` §2.9.

---

## 7. X-6 — Custom HTML in detail blocks (`type: "html"`)

This is the most security-sensitive surface. The Security lane has
reviewed this contract and approved-with-changes; the changes are
absorbed below. The follow-up sanitiser implementation lives in
[`SECURITY.md`](../../SECURITY.md) and the Security-authored
implementation PR (tier 5, human-gated).

> Security verdict: see
> [`forum/REVIEW-security-pr-ux-extensibility-contract.md`](../../forum/REVIEW-security-pr-ux-extensibility-contract.md)
> §1 (Approve-with-changes on the contract; Approve-with-changes on
> E-9 conditional on C-1..C-10; **Reject** the original
> `allow_unsafe_html = True` boolean shape, counter-proposal absorbed
> in §7.3 below).

### 7.1 Non-negotiable invariants

1. **Server is the trust boundary.** Sanitisation happens
   server-side, before the payload leaves Django. The frontend has
   **exactly one** `dangerouslySetInnerHTML` call site — in
   `@dar/details/HtmlBlock.tsx` — and it consumes only
   `block.type === "html"` payloads. Enforced by ESLint
   (`react/no-danger`) allowed exactly once with a justifying
   comment. *(Security C-5.)*

2. **Sanitiser library: `nh3`.** The Python binding for Rust's
   `ammonia`. The `markdown` block type runs through the **same**
   sanitiser — we ship one sanitiser pipeline, not two.
   `bleach` is unmaintained as of 2023 and is not an option.
   *(Security C-1, Q-EXT-01.)*

3. **Closed allowlist, defined in code, not configurable.** Tags
   are pinned in `django_admin_react/sanitiser.py` (the Security
   follow-up PR lands the file). Starting point: `p`, `ul`, `ol`,
   `li`, `strong`, `em`, `a`, `code`, `pre`, `table`, `thead`,
   `tbody`, `tr`, `th`, `td`, `h2`, `h3`, `h4`, `br`, `hr`.
   Attributes allowlisted: `href` on `a` with `http(s):` only,
   `colspan`/`rowspan` on table cells. **No** `style`, **no**
   `class` except a documented allowlist of `dar-*` classes,
   **no** `script`, `iframe`, `object`, `embed`, `form`, event
   handlers, or inline `style`. *(Security C-2.)*

4. **External `<a href>` rewriting.** Every `<a href>` rendered
   from an `html` block is post-processed server-side, **after**
   sanitising: external origins get `rel="noopener noreferrer ugc"`
   and `target="_blank"`; only `http(s):` URLs survive. *(Security
   C-4.)*

5. **CSP is package-emitted, not just recommended.** The package
   emits a `Content-Security-Policy` header on the SPA shell
   response: `default-src 'self'; script-src 'self'; style-src
   'self'; img-src 'self' data:; object-src 'none';
   frame-ancestors 'none'; base-uri 'self'; form-action 'self'`.
   No `'unsafe-inline'`, no `'unsafe-eval'`, no nonces. Consumers
   can override via setting if they truly need to. *(Security C-3,
   Q-EXT-03.)*

6. **Sanitiser version in envelope.** Every `html` block in the
   serialised response carries a `sanitiser_version` field; the
   server logs it per served block. Forward-compat hook for
   bumping the allowlist. *(Security C-6 + Q-EXT-02 Architect
   ask.)*

7. **Latency budget: ≤ 5 ms p99 per block ≤ 8 KiB.** A regression
   target, not an aspiration. *(Security C-7.)*

8. **Audit log per served block.** Format:
   `INFO dar.sanitiser: served html block model=<app>.<model>
   pk=<pk> bytes_in=<n> bytes_out=<m> dropped_tags=<count>
   sanitiser=nh3@<ver>`. Goes through
   `logging.getLogger("dar.sanitiser")`. *(Security C-8.)*

9. **Fail closed.** If sanitising raises, the response carries an
   `ErrorState` block in place of the `html` block. Never
   fall through to raw HTML. *(Security C-9.)*

10. **No client-supplied HTML.** The package's write API rejects
    any client-supplied HTML at the serializer layer. HTML form
    fields are plain text. Round-trip test:
    `<script>alert(1)</script>` stored → returned escaped.

### 7.2 PM/UX-preferred design

Structured-JSON-first: most "custom reports" should be expressed
as `stats`/`table`/`description_list` blocks (§6.1). The `html`
type is the escape hatch, not the default. The Architect should
make `html` feel one step harder to reach than the structured
types in the docs and examples. The shipped example app block is
a `stats` block, not an `html` block (see §6 below + Security
Q-EXT-08).

### 7.3 No "switch off the sanitiser" boolean (Security veto)

The original draft of this contract proposed
`DJANGO_ADMIN_REACT["allow_unsafe_html"] = True` to bypass the
sanitiser. **Security rejected this shape** — a global "switch
off" boolean is the kind of footgun an exhausted consumer reaches
for to "unblock" a broken report and forgets to turn back off.
Counter-proposal absorbed:

> **`type: "trusted_html"`** — a separate, opt-in, register-by-name
> block type. Out of scope for v0.1; available as a v1.x extension
> path. If/when it ships, it MUST satisfy *all* of:
>
> 1. Defined by the consumer via subclassing a `BlockType` base
>    class (Architect-lane API).
> 2. Registered explicitly:
>    `DJANGO_ADMIN_REACT["unsafe_block_types"] = ["myapp.MyTrustedBlock"]`.
> 3. Served to `request.user.is_superuser` only — even if
>    `is_staff` and `has_view_permission`.
> 4. WARNING-level audit log line per served block.
> 5. `SECURITY.md` carries an explicit "no XSS guarantees beyond
>    this point; consumer accepts the risk" disclaimer.

PM/UX recommendation: **no escape hatch in v1.** Consumers who
need truly un-sanitised HTML write a Django view outside the
package. The 80 % consumer pays no complexity tax. If a real
consumer use case proves the need in v1.x, ship the constrained
`trusted_html` type above. Security signed off on either path.

### 7.4 Inline action-invocation security notes (cross-ref X-2)

Pulled forward from Security review §2.2:

- Action invocation endpoint MUST use the same permission class as
  list/detail; do not invent a sibling class.
- `len(pks)` is capped server-side at **1000** (Django HTML admin's
  de-facto limit). Architect codifies the exact constant.
- The requested `action_name` is a lookup, never a substring match,
  against `ModelAdmin.get_actions(request)`.
- Server restricts mutated objects to
  `ModelAdmin.get_queryset(request).filter(pk__in=pks)` and bails
  if the difference is non-empty.

### 7.5 What we never do

- Render server HTML in the SPA without going through the
  sanitiser.
- Accept HTML from the client and echo it back to other users.
- Allow a `ModelAdmin` block to install arbitrary CSS into the
  page — stylesheet additions go through X-1.
- Ship more than one `dangerouslySetInnerHTML` call site in the
  SPA.
- Add a global "switch off the sanitiser" setting (see §7.3).

### 7.6 Resolved questions

The following are now answered (full reasoning in
[`forum/REVIEW-security-pr-ux-extensibility-contract.md`](../../forum/REVIEW-security-pr-ux-extensibility-contract.md)
§4):

- ~~Q-EXT-01~~ (sanitiser): `nh3`, ≤ 5 ms p99 per 8 KiB block.
- ~~Q-EXT-03~~ (CSP `style-src`): no loosening; package emits the
  policy in §7.1 (5).
- ~~Q-EXT-04~~ (`allow_unsafe_html`): boolean rejected; see §7.3
  for the constrained `trusted_html` alternative (v1.x at
  earliest); PM/UX recommends no escape hatch in v1.
- ~~Q-EXT-07~~ (CSRF nonce on action invocation): no; Django's
  session-backed CSRF is sufficient. The view enforces
  `csrf_protect`; integration test "missing `X-CSRFToken` → 403"
  is added in the Security follow-up PR.
- ~~Q-EXT-08~~ (safe example block): one `stats` block on
  `Account` in `examples/fintech/` (see §6.2 below). No `html`
  block example.

All Architect-lane questions are now answered too
([`forum/REVIEW-architect-pr-ux-extensibility-contract.md`](../../forum/REVIEW-architect-pr-ux-extensibility-contract.md)):

- ~~Q-EXT-02~~ (sanitiser_version in envelope): yes, plus
  `sanitiser_profile` forward-hook for the future
  `trusted_html` path. Bump policy: **patch** = sanitiser
  bugfix; **minor** = strictly safer allowlist; **major** =
  broader allowlist or payload shape change — SPA refuses to
  render newer-major blocks and shows an `ErrorState`.
- ~~Q-EXT-05~~ (atomic inline PATCH): single body field on the
  existing `PATCH /api/v1/<app>/<model>/<pk>/`, wrapped in
  `transaction.atomic()`. See §5 above for the body shape.
- ~~Q-EXT-06~~ (detail-block cache): fully consumer-managed via
  `django.core.cache`. No DAR-side cache contract in v0.1.
  Per-block `try/except` is the only server-side guarantee.

All 8 open questions in the original directive are now closed. The
implementation PRs live in the Architect's and Security's lanes
respectively.

### 7.7 Acceptance

Criterion **E-9** in `ACCEPTANCE.md` §2.9, gated on the Security
follow-up PRs landing (sanitiser spec + sanitiser implementation
+ CSP defaults middleware). Until those land, E-9 is **drafted,
not live**; X-6 is implementable but not part of the v0.1 release
gate. PM/UX is comfortable shipping v0.1 with X-1..X-5 + X-7
only, deferring X-6 to a follow-up release. The 80 % consumer
loses nothing.

---

## 7b. X-8 — Custom list filters (`ModelAdmin.list_filter`)

### Goal

Reuse Django's existing `ModelAdmin.list_filter` mechanism — the
same one consumers already write for the HTML admin — to drive
the SPA list page's filter sidebar. **No new filter-definition
DSL.** This is the same posture as X-2 (actions) and X-4
(inlines): we build on top of the Django admin contract; we do
not invent a parallel system.

### Contract (PM/UX requirements — Architect designs the wire
shape in [`docs/api-contract.md`](../api-contract.md))

- The backend exposes filter metadata in the list-page response
  (`GET /api/v1/<app>/<model>/`) under a new `filters` key:

  ```json
  {
    "filters": [
      {
        "name": "status",
        "label": "Status",
        "kind": "choices",
        "choices": [
          {"value": "draft",     "label": "Draft",     "count": 12},
          {"value": "published", "label": "Published", "count": 47}
        ]
      },
      {
        "name": "created_at",
        "label": "Created at",
        "kind": "date_hierarchy",
        "ranges": [
          {"key": "today",     "label": "Today"},
          {"key": "past_7d",   "label": "Past 7 days"},
          {"key": "this_year", "label": "This year"}
        ]
      }
    ]
  }
  ```

  Source: `ModelAdmin.get_list_filter(request)` plus
  `SimpleListFilter` subclasses if any are listed. The Architect
  pins the closed `kind` enum and the `count` semantics.

- The list endpoint accepts filters as **query-string params**:
  `?status=published&created_at=past_7d&q=hello`. This is the
  URL-as-state principle from [`states.md`](states.md) /
  `ACCEPTANCE.md` §2.7 N-3 — reload the page, get the same view.

- Filter values are server-validated against the filter's
  declared choices/ranges; an unknown value returns
  `400 invalid_filter_value`, not 500.

### SPA UX

- The filter sidebar lives on the **right** of the list table on
  desktop (≥ 1024 px); collapses into a "Filters (N)" button
  above the table at < 1024 px ([`responsive.md`](responsive.md)
  R-2 + DESIGN_SYSTEM §6 Layout).
- One section per filter, named by `label`, rendered as:
  - `kind: "choices"` → a list of radio-buttons or checkboxes
    (one selectable for a `SimpleListFilter`, multi-selectable
    for a `BooleanFieldListFilter`-style multi). Counts shown
    next to the label when `count` is present.
  - `kind: "date_hierarchy"` → preset ranges as buttons; "Custom
    range" expands a from/to date-picker (v1 stretch — v0.1 ships
    presets only).
  - `kind: "boolean"` → tri-state ("Yes", "No", "Any").
  - `kind: "search"` → handled by the existing search box, not
    re-rendered as a sidebar filter.
- "Clear all" link clears every applied filter and removes them
  from the URL.
- Active filter values appear as **chips** above the table so the
  user can see what's applied without opening the sidebar; X on
  the chip removes that one filter.
- The chips and the sidebar stay in sync; both edit the same URL
  query-string. The URL is the source of truth.

### What we never do

- Invent a "filter DSL" beyond `ModelAdmin.list_filter`. If a
  consumer needs a custom filter, they subclass
  `SimpleListFilter` exactly as Django docs describe — no new
  base class.
- Accept a filter that isn't in `ModelAdmin.get_list_filter(request)`.
  The server rejects unknown filter names with 400.
- Run a filter through `ModelAdmin.get_queryset(request)` —
  Django already does that; the SPA never reaches into the ORM
  directly.
- Persist filter state outside the URL (no localStorage for
  filters in v0.1 — the URL is enough and shareable).

### Acceptance

New criterion **E-10** in `ACCEPTANCE.md` §2.9:

> Adding `list_filter = ("status", "created_at")` (or a
> `SimpleListFilter` subclass) to an existing `ModelAdmin`
> causes the SPA list page to show the filter sidebar, with no
> frontend change. Applying a filter updates the URL and the
> table.

---

## 8. The "plug-and-play default" invariant

A consumer who *only* runs:

```
pip install django-admin-react
```

and adds the app + URL get:

- No custom CSS (default theme).
- No actions on any model (unless their existing `ModelAdmin`s
  already had them — X-2 is opt-in by definition since most
  `ModelAdmin`s have empty `actions`).
- No inlines visible (unless their `ModelAdmin` already had
  `inlines`).
- No detail blocks (`get_detail_blocks` defaults to `[]`).
- No HTML rendering — the `html` block type is server-side opt-in.

This is the **80 % consumer**. P-1..P-5 must still hold.

A consumer who *opts in* gets the extensibility surface above,
each one independently, without forcing them to learn React or
edit `frontend/`.

---

## 9. What is explicitly NOT extensible in v0.1

- **No React-side plugin / extension API.** Consumers do not
  ship React code, ever. This is the long-standing
  `ARCHITECTURE.md` §8 position; we keep it.
- **No custom widgets** beyond the closed type vocabulary in
  [`docs/api-contract.md`](../api-contract.md) §4. A custom
  field-rendering need is a follow-up to `get_detail_blocks` —
  build a `markdown` or `description_list` block instead.
- **No multi-`AdminSite` support.** v0.1 binds to one configured
  site.
- **No theme runtime swap beyond light/dark.** CSS file is fixed
  per deploy; we don't let users switch themes via the UI in
  v0.1.

---

## 10. Roadmap implications

This document promotes the following items from
`ACCEPTANCE.md` §2.10 v1 non-goals into §2.9 v1 in-scope:

- Inlines (X-4).
- Custom admin actions (X-2) + bulk row selection (X-3).
- A constrained "custom widgets / blocks" surface (X-5 / X-6),
  framed as **detail blocks** rather than as widgets.

Items that **remain** in §2.10 v1 non-goals after this directive:

- React-side plugin / extension API.
- Server-rendered HTML *fallback pages* (we render via the SPA
  using the `html` block type, not as a server-rendered page).
- Runtime Tailwind config swap.
- Multi-`AdminSite` support.
- i18n beyond `LANGUAGE_CODE` defaults.

The promotion of X-4 / X-5 / X-6 may push v0.1 by one PR cycle.
PM/UX recommends sequencing in [`PLAN.md`](../../PLAN.md) §2:

- **PR #9** (new): backend hooks for X-2/X-3.
- **PR #10** (new): backend hooks for X-4 (inlines) + X-5
  (detail blocks).
- **PR #11** (new): X-6 (html block + sanitiser) — Security
  approval gate.
- **PR #6 / #7** (existing): SPA consumes X-1..X-5 as it
  renders.

Final sequencing decision is the Architect's lane — recorded in
the forum thread for this directive.

---

## 11. Acceptance criteria additions (drafted; Architect + Security
co-sign before they land in `ACCEPTANCE.md`)

The following extend `ACCEPTANCE.md` §2.9 "Extensibility UX":

| # | Criterion | How to verify |
| - | --------- | ------------- |
| E-5a | Consumer can swap their `theme_css` file and reload the SPA with no rebuild and no Django restart. | Edit the file, hit reload, see new colours. |
| E-6a | Adding `actions = [my_action]` to an existing `ModelAdmin` causes the SPA list page to show the action dropdown + checkbox column, with no frontend change. | Add `make_published` to `Account`; reload list page. |
| E-6b | An action invocation respects `ModelAdmin.has_*_permission` server-side; the SPA does not even render the action if the user lacks the perm. | Toggle perm, observe. |
| E-6c | An action that defines `short_description` shows that label in the dropdown; an action that raises an exception renders a toast with the message, never crashes the SPA. | Two example actions covering both paths. |
| E-7a | Adding `inlines = [BookInline]` to an existing `ModelAdmin` causes the SPA detail page to render the inline section, with no frontend change. | Add an inline to `Author`; open an author's detail. |
| E-7b | Saving a parent + inline edits hits the server as one atomic PATCH; a validation error on a child rolls back the parent. | Force a child validation error; confirm parent unchanged. |
| E-7c | A `StackedInline` renders as stacked, a `TabularInline` renders as tabular — the SPA respects the consumer's choice. | Two examples in `examples/library`. |
| E-8a | Returning a non-empty `get_detail_blocks` from a `ModelAdmin` causes the SPA detail page to render the blocks in their declared `placement` slot. | Add a `stats` block; observe. |
| E-8b | A block of an unrecognised `type` is silently dropped client-side and logged server-side. | Push a fake `type` in an example; observe console + server log. |
| E-8c | A block whose server-side computation fails renders an `ErrorState` scoped to that block; sibling blocks keep rendering. | Force a block to raise; observe. |
| E-9  | A `type: "html"` block runs through the configured sanitiser before reaching the SPA; `<script>` tags and inline event handlers never survive the round-trip. | Try to slip a `<script>` through; observe stripped output. **Security must sign off** before this row turns from drafted to live. |

---

## 12. Cross-references

- [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) — design tokens,
  primitives, theming.
- [`ARCHITECTURE.md`](../../ARCHITECTURE.md) §5, §8 — extension
  surfaces from the architecture lane (Architect updates).
- [`SECURITY.md`](../../SECURITY.md) — threat model, including the
  sanitiser spec for X-6 (Security updates).
- [`docs/api-contract.md`](../api-contract.md) — endpoint shapes
  Architect adds for X-2 / X-4 / X-5.
- [`forum/UX-DIRECTIVE-extensibility-contract.md`](../../forum/UX-DIRECTIVE-extensibility-contract.md)
  — coordination thread; cross-role open questions live there.
