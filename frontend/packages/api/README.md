# @dar/api — typed REST client + React Query hooks

The only data layer in the SPA. Owns:

- A `dar-mount` reader: discovers the API base URL from the `<meta
  name="dar-mount">` tag the Django index view injects.
- A `fetch` wrapper that:
  - Sends `credentials: 'include'` for session auth.
  - Adds `X-CSRFToken` from the cookie on unsafe methods.
  - Parses the uniform error envelope (`docs/api-contract.md` §6).
- One React Query hook per endpoint:
  - `useRegistry()`
  - `useObjectList({ app, model, query, page, pageSize, ordering })`
  - `useObject({ app, model, pk })`
  - `useCreateObject(...)` / `useUpdateObject(...)` / `useDeleteObject(...)`
- TypeScript types matching `docs/api-contract.md`.

## Rules

- No UI in here. Hooks return plain data + status; pages render it.
- No model-specific code. Everything is generic over `{ app_label,
  model_name, pk }`.
- Types come from `docs/api-contract.md`. Update both in lockstep.
