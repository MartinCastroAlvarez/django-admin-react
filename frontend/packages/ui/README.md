# @dar/ui — Tailwind UI primitives

Generic, reusable, props-driven React components. **No business logic
allowed.** No knowledge of Django, the API, or any consumer model.

## Exports

- **Layout / data:** `Card`, `Table`, `RecordCardList`, `Skeleton`,
  `EmptyState`, `Breadcrumb`.
- **Controls:** `Button`, `Input`, `Checkbox`, `Modal`, `Popover`,
  `Spinner`.
- **Hooks:** `useMediaQuery(query)` — re-renders on a CSS media-query
  match change (e.g. switching the list between `Table` and
  `RecordCardList` at the `md` breakpoint, #421).

`Table` and `RecordCardList` share the same `TableColumn<Row>[]`
descriptor, so a page defines its columns once and renders the table on
wide viewports or stacked record-cards on narrow ones. `RecordCardList`
treats the first column as the card title and the rest as a label/value
list.

Planned components (PR #6 / #7):

- `Button`, `IconButton`
- `Input`, `Textarea`, `Select`, `Checkbox`, `Switch`
- `FormField` (label + control + error + help-text contract)
- `Table` (props-driven columns + rows; no data fetching)
- `Pagination`
- `Toast` / `Toaster`
- `Skeleton`, `Empty`, `ErrorState`
- `Card`, `Stack`, `Cluster`, `Sidebar`, `MainLayout`

## Rules

- Tailwind classes only. No inline `style=` except for CSS variables.
- Every component takes `className` so callers can extend.
- No model-specific code. If you find yourself writing `Account`,
  you're in the wrong package.
- Stateful components hold local UI state only. Server state lives in
  `@dar/api`.
