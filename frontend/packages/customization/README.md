# @dar/customization

The single home for **UI customization that is stored/loaded from
localStorage** — per-device operator preferences, distinct from cached
server data.

## What lives here

- **`usePersistedState` / `usePersistedSet`** — the persistence primitive:
  read-on-mount + write-on-change, every access try/catch-wrapped so
  private mode / quota / SSR degrade to a silent no-op. Consumers used to
  hand-roll this dance in each page.
- **Key registry** (`keys.ts`) — every customization key in one place:
  `THEME_KEY`, `NAV_COLLAPSE_KEY`, `columnsKey`, `filtersKey`,
  `detailCollapseKey`, plus `CUSTOMIZATION_NAMESPACE` and
  `PRESERVED_ON_LOGOUT` (the keys that survive sign-out).
- **`theme`** — light/dark preference + application (`initTheme`,
  `setTheme`, `resolveTheme`, …), moved here as the canonical "stored UI
  preference".
- **`storage`** — low-level `readJSON` / `writeJSON` / `readString` /
  `writeString` / `removeKey` helpers.

## What does NOT belong here

- **Cached server data.** `dar:registry:v1` / `dar:list:v1` /
  `dar:detail:v1:*` are cached API responses owned by `@dar/data`'s SWR
  cache — not preferences. They share the `dar:` namespace but are not
  customization.
- **Network access.** This is a pure leaf: it depends only on `react` +
  the browser `localStorage`. It never imports `@dar/api` or `@dar/data`.

## Who consumes it

- `@dar/settings` (theme toggle), `@dar/sidebar` (nav-group collapse),
  `@dar/web` list (hidden columns, saved filters) + detail (collapsed
  sections), and `@dar/data`'s logout purge (reads `PRESERVED_ON_LOGOUT`
  / `CUSTOMIZATION_NAMESPACE` to decide what to keep).

## Logout interaction

`@dar/data` purges the whole `dar:` namespace on logout **except**
`PRESERVED_ON_LOGOUT` (currently just the theme) — a shared-machine
posture matching Django's server-rendered admin (which caches nothing
client-side). Adding a new preference that should survive logout? Add its
key to `PRESERVED_ON_LOGOUT` here.
