# @dar/list — generic list-view components

Composes `@dar/ui` primitives and `@dar/data` providers into a generic
list page that works for **any** model — entirely driven by the
metadata returned by `GET /api/v1/{app}/{model}/`.

## What lives here

Cohesive, individually-testable building blocks extracted from the
`ListPage` god-component (#428), so the page becomes a thin composition
layer and each unit can be unit-tested in isolation:

- **`DateHierarchyBar`** — the `date_hierarchy` drill-down breadcrumb +
  next-level buckets (Django changelist parity). Props-driven
  (`dh` + `onNavigate`), no router/business coupling.
- **`ListSkeleton`** — first-paint placeholder for the list page (title +
  count, toolbar row, then a card of rows) shown before the columns are
  known. Optional `rows` / `columns` counts; no business coupling.

More units (filter/columns modals, the `list_editable` controller) land
here as the decomposition progresses. (Generic, business-free primitives
like `Pagination` live in `@dar/ui`, not here.)

## Rules

- **`@dar/data` is the only data source.** Never import `@dar/api`
  directly. See [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §5.2a.
- No model-specific code. Columns, search fields, ordering are all
  read from the API response (via `@dar/data`).
- The component receives `{ app, model }` and nothing else from the
  router. Everything else comes from
  `useObjectListData({ app, model, ... })`.
- No business logic here — purely presentation + state plumbing.
