# Agent claim — Opus 4.7 (data layer)

Posted: 2026-05-25
Branch: shared working tree (no commits yet; will coordinate before push)
Agent id: `claude-data-opus47`

## Why

The repo owner sent a new requirement after `claude-foundation-opus47`
had already laid down the frontend skeleton:

> in the react app, make sure there is a `packages/data/` with context
> providers, so that the app will only interact with the context providers
> of this layer. This layer acts as a database for the web app. It persists
> data in localstorage so that it can show data as soon as the user loads
> the page and eventually update it with the data from react query once it
> is back from the API + it debounces updates to the `packages/api/`
> mutations.

This adds a new package `@dar/data` and reorders the data-layer rule:
**components consume `@dar/data` providers; only `@dar/data` consumes
`@dar/api`.** That changes the spirit of `CLAUDE.md §7` ("React Query is
the only data layer") and `ARCHITECTURE.md §5.1`.

## Scope I'm taking

Additive, parallel-safe:

- `frontend/packages/data/` — new package skeleton (package.json,
  tsconfig.json, README.md, src/index.ts).
- `docs/data-layer.md` — design doc for hydration, debounced flush,
  conflict rules.
- `docs/agents/decisions.md` — append the decision.
- `docs/agents/changelog.md` — entry.

Edits to shared files (small, additive — diff will be obvious):

- `frontend/packages/README.md` — add `@dar/data` to the table and the
  dependency-order diagram.
- `frontend/README.md` — add `data/` to the Layout block.
- `ARCHITECTURE.md §5.1` — append a bullet listing `@dar/data`.
- `CLAUDE.md §7` — soften "React Query is the only data layer" to
  "components consume `@dar/data`; `@dar/data` is the only thing that
  imports `@dar/api`/React Query."

## To `claude-foundation-opus47` (if still active)

- If any of the shared-file edits collide with your in-flight changes,
  leave a counter-claim here and I will rebase my edits onto yours.
- I will not commit until you have committed your PR 1 work (or the
  repo owner directs otherwise).

## To the repo owner

- Nothing is committed yet on either branch. The GitHub PAT
  embedded in `.git/config` needs to be rotated before any push.
  Once rotated, please run `gh auth login` and I will push via gh.

— `claude-data-opus47`
