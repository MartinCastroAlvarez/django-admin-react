# Frontend data layer (`@dar/data`)

This document is the design contract for `frontend/packages/data/`
(`@dar/data`). It expands on `ARCHITECTURE.md` §5.1 / §5.2a and is the
file consumed by reviewers and frontend agents working on PRs #6 / #7.

> Single rule, repeated: **UI packages read and write through `@dar/data`
> only. Only `@dar/data` imports `@dar/api`.** A CI lint rule enforces
> this in PR #6.

---

## 1. Why this layer exists

Without `@dar/data`, every UI component would subscribe directly to a
React Query hook. That works, but it conflates three concerns:

1. **Network state** (in-flight, succeeded, failed, retrying).
2. **Persistence** (what we should render on the next cold load).
3. **User intent buffering** (the user typed 5 keystrokes; we want
   1 `PATCH`, not 5).

`@dar/data` splits these out:

| Concern              | Owned by      | Visible to UI as              |
| -------------------- | ------------- | ----------------------------- |
| Network              | `@dar/api`    | hidden behind `@dar/data`     |
| Persistence          | `@dar/data`   | `data`, `fromCache`           |
| Intent buffering     | `@dar/data`   | `useUpdateField`, `flushNow`  |

The UI keeps rendering instantly, the network gets called the minimum
number of times, and the persistence layer is one file we can audit for
"do not store secrets" once instead of in every page.

---

## 2. Storage layout

All keys live under the `dar:v1:` prefix so a future schema change can
invalidate by prefix without touching unrelated localStorage state.

| Key                                                  | Value shape                              |
| ---------------------------------------------------- | ---------------------------------------- |
| `dar:v1:registry`                                    | `{ mount, user, apps[] }`                |
| `dar:v1:list:<app>.<model>:<query-hash>`             | `{ page, page_size, total, columns, results[], cachedAt }` |
| `dar:v1:detail:<app>.<model>:<pk>`                   | `{ fields, fieldsets, permissions, cachedAt }` |
| `dar:v1:pending:<app>.<model>:<pk>`                  | `{ patch: {...}, attemptCount, lastError? }` |

`<query-hash>` is a stable 8-character hash of
`{ q, page, page_size, ordering }`. Pages with different queries do not
share cache entries.

`cachedAt` is an ISO 8601 timestamp. A 24-hour soft TTL applies: older
entries still hydrate the UI but the cache is treated as stale and a
revalidation is triggered.

---

## 3. Hydration flow (read path)

```
                ┌────────────────────────────────────────┐
component  ────►│ useObject({ app, model, pk })          │
                └─────────────┬──────────────────────────┘
                              ▼
              ┌──────────────────────────────┐
              │ ObjectProvider               │
              ├──────────────────────────────┤
              │ 1. Sync read from localStorage│
              │ 2. Emit {data, fromCache:true,│
              │    isStale: ?, isPending:true}│
              │ 3. Subscribe to @dar/api      │
              │    useObject(...) query       │
              │ 4. When server resolves:      │
              │     - merge response          │
              │     - write to localStorage   │
              │     - emit {fromCache:false}  │
              └──────────────────────────────┘
```

Notes:

- The provider returns immediately on first render even if no cached
  entry exists — `data` is `null` in that case and `isPending` is true.
- If the cached entry is older than the soft TTL, the provider sets
  `isStale: true` and the UI may show a subtle indicator.
- The provider deduplicates concurrent subscriptions to the same key.

---

## 4. Mutation flow (write path)

```
component                        provider                   @dar/api
   │                                │                            │
   │ useUpdateField("balance",10)   │                            │
   ├────────────────────────────── ►│ (1) update in-memory       │
   │                                │     emit new {data, isDirty}│
   │                                │ (2) write localStorage     │
   │                                │ (3) start/restart debounce │
   │                                │     timer (default 300ms)  │
   │ ...user types more...          │                            │
   │ useUpdateField("balance",12)   │                            │
   ├────────────────────────────── ►│ coalesced — timer resets   │
   │                                │                            │
   │                                │ (4) on timer fire:         │
   │                                │     PATCH via @dar/api  ──►│
   │                                │                            │
   │                                │ (5a) on success: merge      │
   │                                │      server response,       │
   │                                │      clear isDirty, drop    │
   │                                │      pending:* key          │
   │                                │ (5b) on failure: roll back  │
   │                                │      to pre-edit value,     │
   │                                │      emit error, surface    │
   │                                │      toast via @dar/ui      │
```

### 4.1 Debounce policy

- Default debounce: **300ms** for field edits.
- **0ms (immediate)** for explicit submit/delete buttons. `useCreate`,
  `useDelete`, and form `submit()` all flush synchronously.
- `flushNow(scope?)` is exposed so the shell can flush on
  `beforeunload` or on navigation away from the form.
- `cancel(scope?)` discards pending writes when the user clicks
  "discard changes".

### 4.2 Coalescing rules

Multiple edits to the same field within the debounce window collapse to
the latest value. Edits to **different fields** of the same object
collapse to a single `PATCH` whose body is the merged diff.

### 4.3 Rollback rules

- Server returned `400 validation_failed`: roll back the rejected
  fields only; keep other in-flight edits; surface field-level errors.
- Server returned `403`: roll back everything in the pending key;
  surface a permission toast; remove the `pending:*` localStorage entry
  so we don't retry on reload.
- Server returned `409 conflict` (reserved for v1.x): not applicable
  in v1; behaves like `400`.
- Network failure: keep the `pending:*` localStorage entry and retry
  on the next mount with exponential backoff capped at 3 attempts. If
  the third attempt fails, roll back and notify the user.

---

## 5. Sensitive-field discipline

`@dar/data` is the choke point for what lands in localStorage. It must:

- **Never persist** anything not present in the API response. The API
  already strips `password`, `secret`, `token`, `api_key`, `hash` and
  any `exclude`d/`readonly` field; `@dar/data` does **not** invent
  those fields on the client.
- **Never persist** the CSRF token or anything cookie-bound. Those are
  Django's responsibility.
- Provide a `clearAll()` helper that wipes the entire `dar:v1:`
  namespace. The shell calls this on logout.

If a future field type would carry sensitive data (e.g., one-time tokens
for a future "rotate API key" widget), the design must add an explicit
opt-out marker rather than blanket-trusting the API response. See
`SECURITY.md` §2.7.

---

## 6. Public API (planned)

```ts
// Provider — wrap once near the root, inside <QueryClientProvider />.
<DataProvider>
  <App />
</DataProvider>

// Reads
const { data, isPending, isStale, fromCache, error } = useRegistry();
const { ... } = useObjectList({ app, model, query });
const { ... } = useObject({ app, model, pk });

// Writes
const updateField = useUpdateField({ app, model, pk });
const create      = useCreateObject({ app, model });
const remove      = useDeleteObject({ app, model, pk });

// Imperative cache control (rare; used by shell on logout/auth events)
const { flushNow, cancel, invalidate, clearAll } = useDataActions();
```

Each `useObject*` hook returns the same SWR-shaped object so pages can
treat all three uniformly.

---

## 7. Testing matrix (lands with the implementation in PR #6 / #7)

For every provider:

- First render with empty localStorage → `data: null`, `isPending: true`.
- First render with valid cached payload → `data: <cached>`,
  `fromCache: true`, `isPending: true`, then `fromCache: false` once
  the network resolves.
- First render with cached payload older than TTL → `isStale: true`.
- Optimistic update + immediate read → reflects new value.
- Debounce window: 5 edits in 200ms produce **1** mutation call with the
  final value.
- Server 400 → rollback for affected fields only.
- Server 403 → full rollback + toast + drop pending entry.
- Server 500 → retry up to 3 times then rollback.
- `clearAll()` removes every `dar:v1:*` key (and only those).

---

## 8. Out-of-scope for v1

- IndexedDB instead of localStorage — keep v1 simple; revisit if storage
  quota is an issue with image-heavy admins.
- Cross-tab synchronisation via `BroadcastChannel`. Nice-to-have; defer.
- Offline queue persistence across browser restarts beyond the
  `pending:*` keys — current behaviour persists; v1.x can add a UI for
  inspecting queued writes.
- Conflict resolution beyond "last write wins". v1.x can introduce
  field-level versioning if the consumer enables optimistic concurrency
  in the API (reserved `409 conflict`).

---

## 9. Cross-references

- `ARCHITECTURE.md` §5.1, §5.2a — package layout + data-layering rule.
- `CLAUDE.md` §7 — one-line agent contract for the rule.
- `docs/api-contract.md` — the wire protocol `@dar/data` consumes via
  `@dar/api`.
- `SECURITY.md` §2.7 — serialization rules that govern what can land in
  localStorage.
