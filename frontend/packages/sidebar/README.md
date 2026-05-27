# @dar/sidebar

The SPA **navigation chrome** — everything to the left of the page
content.

## What lives here

- `Sidebar.tsx` — a single `<Sidebar/>` that renders:
  - the brand header (title + logo from the `dar-brand-*` meta tags);
  - the signed-in user line;
  - the per-user action buttons (**Settings** cog → `@dar/settings`
    modal; **Install app** when the PWA `beforeinstallprompt` fired);
  - the model **filter** input (shown at/above `FILTER_THRESHOLD`
    models — Django admin sidebar parity);
  - the metadata-driven app → model **nav** (routes by the model's real
    app label, honouring `get_app_list` groupings);
  - the responsive **drawer**: a static column at ≥lg, an off-canvas
    slide-in (with backdrop + hamburger top bar) below lg, Esc-closable.

The component is self-contained: it owns its own drawer / filter /
settings open state. The app shell only places `<Sidebar/>` next to its
`<main>`.

## What does NOT belong here

- The page content region (`<main>`) — that's the app shell (`Layout`).
- The Settings dialog itself — that's `@dar/settings` (this package only
  renders it on cog click).
- The API client. Per CLAUDE.md §7 a UI package imports only `@dar/data`
  (registry) + `@dar/ui` + its sibling UI packages — never `@dar/api`.
- Model-aware list/detail rendering — those live in `@dar/list` /
  `@dar/details`.

## Pointers

- Consumed by `apps/web/src/Layout.tsx`.
- Reads the registry via `@dar/data`'s `useRegistry()`.
