# docs/consumer/

External-consumer feedback on integrating `django-admin-react` into a real
Django application. Each file in this folder is a snapshot of what a
production Django shop expects from the library when they try to wire it
up alongside their existing legacy admin.

## What lives here

- Generic functional-requirement docs filed by adopters trying to use
  this library on a real codebase. Each doc is anonymized — it speaks
  in generic Django/React terminology and avoids any business specifics
  from the consumer's app.
- Links to the matching GitHub issues that capture the same
  requirement in tracker form (the doc is the *summary*; the issues
  are the *workstreams*).

## What does NOT belong here

- Internal architecture, threat-model, or roadmap docs — those live in
  `../`, `../ux/`, and `../agents/`.
- Acceptance criteria. Those live in [`../../ACCEPTANCE.md`](../../ACCEPTANCE.md);
  consumer requests should *flow into* ACCEPTANCE updates over time,
  not duplicate the spec here.
- PII / proprietary domain details from any consumer's app.

## Conventions

- One markdown file per consumer integration round, named
  `requirements-<integration-name>-<YYYY-MM-DD>.md`.
- Cross-link the matching GitHub issues by number (`#54`, `#55`, …).
- A short
  [Discussion](https://github.com/MartinCastroAlvarez/django-admin-react/discussions)
  (Announcements category) is the canonical public surface for a new
  consumer-feedback drop; the detailed doc lives here.

## See also

- [`../agents/open-questions.md`](../agents/open-questions.md) — open
  decisions agents are tracking; consumer feedback may surface new
  questions here.
- [`../../ACCEPTANCE.md`](../../ACCEPTANCE.md) — the formal acceptance
  spec. Consumer feedback is one of the inputs that drives changes
  here.
- [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
  — when a consumer-feedback item is accepted into scope, it gets a
  card (Phase = the target version).
