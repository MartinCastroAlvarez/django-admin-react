# API_CONTRACT.md

> ### The canonical API contract lives in the API repo (post-#544)
>
> The JSON REST API surface — every endpoint shape, the field-type
> vocabulary, the uniform error envelope, pagination / ordering / search
> rules, and the additive-only forward-compatibility promise — is the
> **`django-admin-rest-api`** package's contract. The canonical document
> is therefore in the API repo, not here.
>
> **Read it at:** [`MartinCastroAlvarez/django-admin-api → docs/api-contract.md`](https://github.com/MartinCastroAlvarez/django-admin-api/blob/main/docs/api-contract.md)
>
> Any change to the wire shape must land in that repo's PR. This SPA
> repo consumes the contract; it does not own it.

## Why this pointer still exists

A contributor or AI agent scanning this repo's root might still expect
an `API_CONTRACT.md` here. This file stays as a one-click hop to the
real document so nobody is confused about where to look.

## During the #544 migration

While [META #544](https://github.com/MartinCastroAlvarez/django-admin-react/issues/544)
is in flight, a copy of the contract still lives temporarily at
[`docs/api-contract.md`](docs/api-contract.md). That copy is being
retired phase-by-phase as the local `django_admin_react/api/` tree is
removed. **Treat the API repo's copy as authoritative** from this point
forward — any drift between the two is a bug in the migration, not a
license to fork the contract.

## What stays in this repo (SPA side)

- The TypeScript mirror of the contract under
  [`frontend/packages/api/src/contract.ts`](frontend/packages/api/src/contract.ts).
  It must match the canonical API-repo document; the codebase enforces
  this via the boundary lint and typecheck gates.
- The SPA's consumer of each endpoint (React Query hooks, `@dar/data`,
  `@dar/api`). These call the wire shape, they don't define it.

## Stability promise (unchanged)

- Within `api/v1/`: **additive only.** New optional response fields and
  query params are fine; renames / removes / type changes are not — they
  require a new namespace (`api/v2/`).
- Breaking changes appear in the API repo's `CHANGELOG.md` and require a
  major version bump from `1.0.0` onward.

## Tests asserting the contract

The API repo owns the request/response shape tests. This repo's tests
exercise the SPA's behaviour against the contract (via the same wire,
read by the TS mirror). See [`TESTING.md`](TESTING.md) §3.
