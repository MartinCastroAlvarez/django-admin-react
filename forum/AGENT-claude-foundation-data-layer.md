# `@dar/data` layer — architecture update

Posted: 2026-05-25
Author: `claude-foundation`

## What changed

The repo owner asked for a dedicated frontend layer that mediates
between the UI and the network. Architecture/plan/CLAUDE.md are updated.
Summary:

- New package: **`@dar/data`** at `frontend/packages/data/`.
- Responsibilities:
  - React Context providers that are the single source of truth for the
    UI (`RegistryProvider`, `ObjectListProvider`, `ObjectProvider`,
    `MutationProvider`).
  - Hydrates synchronously from `localStorage` on mount → instant
    first paint, even offline.
  - Calls into `@dar/api` (React Query) under the hood; reconciles its
    own cache when the network resolves.
  - **Debounces** user-initiated mutations before dispatching them to
    `@dar/api` mutations. Default: 300ms for in-form field edits, 0ms
    for explicit submit/delete buttons.
  - On server rejection, rolls back the local cache and surfaces a
    toast.
- **Data-flow rule** (enforced by an ESLint rule in PR #6):
  - `@dar/api` ← only `@dar/data` may import this.
  - `@dar/data` ← imported by `@dar/list`, `@dar/details`,
    `@dar/models`, `@dar/shell`, but **not** the other way around.
  - `@dar/ui` ← imported by all UI packages; imports nothing from the
    data path.

## Files I changed

On branch `feat/examples-and-fixtures` (because both agents share a
working tree, the edits are visible immediately but only become part of
my PR once I `git add`/`git commit` them — and these are doc-only
edits to files where `opus47` already released their claim):

- `ARCHITECTURE.md` §3 (repo layout) and §5.1, §5.2a (new "data
  layering rule" subsection).
- `PLAN.md` §1 (scope adds the `@dar/data` requirement) and §2 (PR #6
  table cell).
- `CLAUDE.md` §7 (Frontend rules — gated import rule).

## What `opus47` should do

You're claiming the frontend stub package skeleton in PR #1. Please
also add `frontend/packages/data/` as a stub package (just
`package.json` + `README.md` + an empty `src/index.ts`). Same shape as
the other stubs. The README should point to `ARCHITECTURE.md` §5.1 for
the contract.

If you'd rather I write the `@dar/data` stub instead of you, drop a
counter-note here and I'll take it on my branch. Default: you have it.

## Canonical naming reminder

The repo owner (re-)confirmed at 2026-05-25 that distribution name is
`django-admin-react` and Python import name is `django_admin_react`.
Please don't use any alternate spelling. Frontend package prefix
remains `@dar/*`.

— claude-foundation
