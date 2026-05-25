# @dar/list — generic list-view components

Composes `@dar/ui` primitives and `@dar/data` providers into a generic
list page that works for **any** model — entirely driven by the
metadata returned by `GET /api/v1/{app}/{model}/`.

## Rules

- **`@dar/data` is the only data source.** Never import `@dar/api`
  directly. See [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §5.2a.
- No model-specific code. Columns, search fields, ordering are all
  read from the API response (via `@dar/data`).
- The component receives `{ app, model }` and nothing else from the
  router. Everything else comes from
  `useObjectListData({ app, model, ... })`.
- No business logic here — purely presentation + state plumbing.
