# @dar/models — registry / navigation

Renders the sidebar + landing page that lists apps and models the user
can see. Driven by `useRegistryData()` from **`@dar/data`**.

## Rules

- **`@dar/data` is the only data source.** Never import `@dar/api`
  directly. See [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §5.2a.
- Reads the registry response only. Doesn't know what `Account` or
  `Book` are.
- Hides models for which `permissions.view` is false.
- The "Add" entry only renders when `permissions.add` is true.
