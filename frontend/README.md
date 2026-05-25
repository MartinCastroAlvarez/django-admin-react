# frontend/ — pnpm workspace for the React SPA

This directory contains the source for the React single-page app that
the Django package serves. **It is not shipped to PyPI** — only the
built bundle (copied into
`django_admin_react/static/admin_react/`) is.

## Layout

```
frontend/
├── pnpm-workspace.yaml
├── package.json              # Root scripts, dev dependencies
├── .npmrc                    # Locks to pnpm, no npm/yarn drift
├── tsconfig.base.json        # Shared TS compiler options
└── packages/
    ├── shell/    # @dar/shell    — App entry, router, auth boundary, builds with Vite
    ├── ui/       # @dar/ui       — Tailwind primitives. No business logic.
    ├── api/      # @dar/api      — Typed REST client + React Query hooks
    ├── list/     # @dar/list     — Generic list-view components
    ├── details/  # @dar/details  — Generic detail/create/update components
    └── models/   # @dar/models   — Registry/sidebar navigation components
```

## Rules

- **pnpm only.** No `npm`/`yarn`. The `.npmrc` enforces this; CI will
  fail on `package-lock.json` or `yarn.lock`.
- **No model-specific code.** No frontend package may import or
  hardcode `Account`, `Book`, `Transaction`, or any consumer model.
  The UI is metadata-driven.
- **TypeScript `strict: true`.** No `any` in shipped code.
- **React Query is the only data layer.** No Redux, Zustand, etc.
- **Tailwind for styling.** Theme overrides via CSS variables; full
  config replacement is out of scope for v1 (see `ARCHITECTURE.md`
  §5.3).

## Development

```bash
pnpm install
pnpm -r lint
pnpm -r typecheck
pnpm -r build
```

Build pipeline, Vite config, ESLint, and Tailwind setup all land in
PR #6 (see [`PLAN.md`](../PLAN.md) §2).

## Shipping to the Python package

```bash
pnpm --filter @dar/shell build
# Copy frontend/packages/shell/dist/ → django_admin_react/static/admin_react/
# (handled by a script that lands in PR #6)
```

The Python package on PyPI contains the pre-built bundle so consumers
never need Node to install.
