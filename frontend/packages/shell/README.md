# @dar/shell — SPA entry point

The only buildable React app in the workspace. Composes the other
`@dar/*` packages into a single bundle that the Django package serves.

## Responsibilities

- React Router setup (history mode; reads base path from
  `<meta name="dar-mount">`).
- Auth boundary: if the API returns 401/403, redirect to the Django
  admin login URL with `?next=` set to the current SPA path.
- Theme bootstrap: load CSS variables, allow consumer overrides via the
  Django template (PR #6).
- React Query client configuration (default stale-time, retry,
  refetch-on-window-focus).
- Layout shell (sidebar via `@dar/models`, main pane via `@dar/list` /
  `@dar/details`).

## Build

```bash
pnpm --filter @dar/shell build
# Output: frontend/packages/shell/dist/
# A poetry script will copy that into django_admin_react/static/admin_react/
```

Vite, Tailwind, ESLint, and the build-to-Django-package script all land
in PR #6.
