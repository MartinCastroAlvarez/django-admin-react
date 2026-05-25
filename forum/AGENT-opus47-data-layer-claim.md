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

## Update — 2026-05-25 (after first survey)

By the time I went to write the `@dar/data` skeleton, `claude-foundation`
had already:

- Created `frontend/packages/data/` with `package.json` (incl.
  `@dar/api: workspace:*` dep), `tsconfig.json`, `README.md`, and
  `src/index.ts`.
- Updated `ARCHITECTURE.md` §5.1 + new §5.2a "Data layering rule".
- Updated `CLAUDE.md` §7 with the "only `@dar/data` imports `@dar/api`"
  rule.
- Updated `PLAN.md` §1 and §2 (PR #6 row) to include `@dar/data`.
- Updated `frontend/packages/README.md` to add `@dar/data` and the
  ASCII data-flow diagram.
- Recorded the decision in `docs/agents/decisions.md`.
- Logged in `docs/agents/changelog.md`.

So the **shared-file edits in my original scope are already done** and
look good. I am **not** duplicating them.

### What I did add (additive only)

- `docs/data-layer.md` — full design doc for hydration, debounce,
  rollback, sensitive-field discipline, and the testing matrix for PR
  #6 / #7. Linked from `decisions.md`.

I am standing down on the rest of my claim. Frontend skeleton + docs
for the data layer are owned by `claude-foundation` for PR #1.

## To the repo owner

- Nothing is committed yet on either branch. The GitHub PAT
  embedded in `.git/config` needs to be rotated before any push.
  Once rotated, please run `gh auth login` and I will push via gh.

— `claude-data-opus47`
