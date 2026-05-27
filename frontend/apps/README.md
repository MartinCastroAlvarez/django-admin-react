# frontend/apps/

Runnable applications in the pnpm workspace (as opposed to the reusable
libraries under [`../packages/`](../packages/)).

What lives here:

- [`web/`](web/) — `@dar/web`, the single-page React admin app. It is the
  Vite entry point that composes the `@dar/*` packages into pages and
  builds the bundle shipped inside the Python package
  (`django_admin_react/static/`). Page composition currently lives here;
  `@dar/list` / `@dar/details` / `@dar/models` are reserved for future
  extraction (see [`../packages/README.md`](../packages/README.md)).

What does **not** belong here:

- Reusable, model-agnostic components or data logic — those belong in
  [`../packages/`](../packages/) (`@dar/ui`, `@dar/data`, `@dar/sidebar`,
  `@dar/settings`, …).
- Direct `@dar/api` imports — apps consume the backend **only** through
  `@dar/data` (the CI-enforced data-flow boundary, `CLAUDE.md` §7).
- Knowledge of example models (`Account`, `Book`, …) — the UI is
  metadata-driven; if the API doesn't provide needed metadata, fix the
  API, not the app.

Pointers: [`../packages/README.md`](../packages/README.md) (package
layering + dependency rules), [`../../CLAUDE.md`](../../CLAUDE.md) §7
(frontend rules).
