# @dar/search

The list-view **search + filter UI**: the search input and the inline,
per-filter **dropdown buttons** (each opening a small options popover),
replacing the old full-screen filter modal. The list page composes
`<FilterBar>` and owns the URL/query state; this package owns the
presentation + interaction so the page (and `@dar/list`) don't grow.

## What lives here
- `FilterBar` — the search input + a row of filter dropdown buttons +
  "Clear all".
- (internal) `FilterDropdown` — one filter's button + its options popover.

## What does NOT belong here
- URL / query-param state — the page owns it and passes values +
  `onFilterChange` / `onSearchChange` callbacks in.
- Network calls — those go through `@dar/data`.

Imports only `@dar/data` (types) + `@dar/ui` (`Input`, `Popover`), per
CLAUDE.md §7. Single-select per filter, matching Django's `list_filter`.
