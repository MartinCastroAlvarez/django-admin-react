# @dar/history

The object-history surface — Django admin's per-object **History** view.

## What lives here

- **`HistoryModal`** — opened from the detail page; reads
  `GET <app>/<model>/<pk>/history/` (the `LogEntry` timeline via
  `@dar/data`) and renders the change log in the shared `@dar/ui` `Modal`.

## What does NOT belong here

- **Detail-page orchestration.** The detail page itself lives in
  `@dar/web` (slated to move to `@dar/details` — issue #303); it composes
  `<HistoryModal/>`, it doesn't live here.
- **Direct network access.** Per CLAUDE.md §7, never import `@dar/api`;
  history data comes through `@dar/data` (`useApiClient`,
  `HistoryResponse`).

## Dependencies

`@dar/history` → `@dar/data` (history endpoint + types), `@dar/ui`
(`Modal`, `Button`, `Spinner`). Consumed by `@dar/web`.

## Pointers

- History wire shape: `@dar/data` (`HistoryResponse`).
- The endpoint: `django_admin_react/api/views/history.py` (#244).
- Generic modal/primitives: [`@dar/ui`](../ui/README.md).
