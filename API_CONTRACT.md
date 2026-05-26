# API_CONTRACT.md

This file is a **pointer** to the canonical API contract document. The
long-form contract lives under [`docs/api-contract.md`](docs/api-contract.md)
so it can sit next to the rest of the long-form docs.

This top-level pointer exists so that a contributor scanning the repo
root finds the contract without having to dig.

> If you are an AI agent: the canonical contract is
> [`docs/api-contract.md`](docs/api-contract.md). Any change to the
> wire shape **must** update that file in the same PR, per
> [`ACCEPTANCE.md`](ACCEPTANCE.md) §3.4 C-1.

## What the contract covers

- HTTP endpoints under the consumer-chosen mount (default examples
  use `/admin-react/api/v1/`).
- Request and response JSON shapes.
- The closed v1 field-type vocabulary (`string`, `integer`,
  `decimal`, `boolean`, `date`, `datetime`, `uuid`, `choice`,
  `foreignkey`, `unsupported`).
- The uniform error envelope.
- Pagination, ordering, search rules.
- Forwards-compatibility rules (additive only within `api/v1/`).

## Stability promise

- Within `api/v1/`: **additive only**. New optional response fields
  and query params are fine; renames / removes / type changes are
  not — they require a new namespace (`api/v2/`).
- Breaking changes are documented in the top-level `CHANGELOG.md`
  (added with the first release) and require a major version bump
  from `1.0.0` onward.

## Who owns this

- **Specification** — Software Architect agent
  ([`agents/software-architect/`](agents/software-architect/)).
- **Implementation** — Architect, with Security review for
  permission and serialization paths.
- **Consumer expectations** — Product Manager agent verifies the
  contract supports the documented user flows
  ([`docs/ux/primary-flows.md`](docs/ux/primary-flows.md)).

## Tests asserting the contract

See [`TESTING.md`](TESTING.md) §3 (mandatory test matrix). Integration
tests under `tests/test_*.py` assert each endpoint's request/response
shape against the contract.
