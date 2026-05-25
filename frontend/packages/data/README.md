# @dar/data — context-provider data layer

The **only** layer the React UI talks to. Composes `@dar/api`
(server state via React Query) with React Context + `localStorage`
to give the rest of the SPA a stale-while-revalidate database with
instant first paint and debounced writes.

## Contract

Every page-level package (`@dar/list`, `@dar/details`, `@dar/models`,
`@dar/shell`) must read and write through `@dar/data` only. **No
page-level package may import `@dar/api` directly.** This keeps the
caching and persistence strategy in one place and makes the rest of
the app side-effect free.

```
        ┌──────────────────────────────────────────────┐
        │ pages: @dar/list, @dar/details, @dar/models  │
        │ shell:  @dar/shell                           │
        └─────────────────────▲────────────────────────┘
                              │ read/write context
                              │
        ┌─────────────────────┴────────────────────────┐
        │ @dar/data — React Context + localStorage     │
        │   - reads from localStorage on first render  │
        │   - revalidates via @dar/api (React Query)   │
        │   - debounces user-driven mutations          │
        └─────────────────────▲────────────────────────┘
                              │
        ┌─────────────────────┴────────────────────────┐
        │ @dar/api — typed fetch + React Query hooks   │
        └──────────────────────────────────────────────┘
```

## Behaviors

### Stale-while-revalidate (SWR)

- On first render, `@dar/data` reads any previously cached payload from
  `localStorage` under a namespaced key (e.g.,
  `dar:v1:registry`, `dar:v1:list:<app>.<model>:<query-hash>`,
  `dar:v1:detail:<app>.<model>:<pk>`).
- The provider exposes that cached value immediately so the UI can
  render without a spinner.
- In the background it triggers the matching React Query fetch.
- When the fetch resolves, it both updates the in-memory context value
  and writes the fresh payload to `localStorage`.

### Debounced writes

- For form edits, `@dar/data` exposes setters that batch / debounce
  before calling `@dar/api` mutations. Default debounce: 500ms.
- The setter optimistically updates the in-memory context and
  `localStorage` first, so the UI feels instant.
- On debounce flush, it issues the `PATCH` (or `POST`/`DELETE`) and
  reconciles the response (server may normalize values).
- On error, the optimistic update is rolled back and the error is
  surfaced to the consuming page.

### Cache invalidation

- Mutations on a model invalidate the matching list-cache key in
  `localStorage` as well as React Query's cache.
- The provider exposes an `invalidate(scope)` for cases where another
  side effect requires it (e.g., navigating into a new model).

## Storage rules

- Versioned key prefix (`dar:v1:...`) so we can bump the cache without
  collisions.
- **Never store anything sensitive** in `localStorage`:
  - No session tokens (we use Django's `sessionid` cookie — never
    touched by JS).
  - No CSRF tokens.
  - No fields that match the API serializer's sensitive denylist
    (`password`, `secret`, `token`, `api_key`, `hash`, …). The API
    already strips them; this is defense in depth.
- A `clearAll()` helper wipes the entire `dar:` namespace on logout.
- Cache TTL: 24h soft TTL; entries older than 24h are treated as a
  miss but still rendered while revalidating.

## Rules

- No UI in here. Providers and hooks only.
- No model-specific code. Everything is generic over `{ app, model,
  pk }`.
- Page packages **must not** import `@dar/api` directly. If you find
  one that does, fix it.
- All persistence goes through this package's helpers — direct
  `localStorage.setItem` from elsewhere is a review-blocking comment.

## API surface (planned for PR #6 / #7)

```ts
// Providers
<DataProvider>{children}</DataProvider>

// Hooks (return SWR-shaped state)
useRegistryData()
useObjectListData({ app, model, query, page, pageSize, ordering })
useObjectData({ app, model, pk })

// Mutations (debounced)
useCreateObjectData({ app, model })
useUpdateObjectData({ app, model, pk, debounceMs? })
useDeleteObjectData({ app, model, pk })

// Cache control
invalidate(scope)
clearAll()
```

Each `use*Data` hook returns `{ data, isLoading, isStale, error,
fromCache }` so pages can show a small "syncing" indicator without
hiding the cached content.
