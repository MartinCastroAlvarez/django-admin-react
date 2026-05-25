# docs/agents/ — durable inter-agent coordination

This folder is the canonical home for cross-session, cross-agent
artifacts. Anything here is committed, public, and append-mostly.

## Files

- [`decisions.md`](decisions.md) — accepted architectural decisions.
  Append-only. Each entry has a date, a one-line summary, and a link to
  the PR or thread where the decision was made.
- [`open-questions.md`](open-questions.md) — questions that need a
  decision. When a question is answered, move its summary line to
  `decisions.md` and remove it from here.
- [`changelog.md`](changelog.md) — one line per meaningful PR. Newest
  on top. This is the at-a-glance history a new agent reads first.

## When to write where

| You want to…                                          | Write here              |
| ----------------------------------------------------- | ----------------------- |
| Record an accepted, durable design choice             | `decisions.md`          |
| Surface an unresolved question                        | `open-questions.md`     |
| Note that a PR shipped                                | `changelog.md`          |
| Coordinate ephemerally with another agent             | `/forum/AGENT-*.md`     |
| Explain how a folder works                            | that folder's `README`  |
| Document the overall architecture                     | `/ARCHITECTURE.md`      |

## What does **not** belong here

- Secrets, tokens, credentials, or `.env` content.
- Long prose that's really architecture — push that into
  `/ARCHITECTURE.md`.
- Transient agent state (use `/forum/`).
- PR text — that belongs in the PR description on GitHub.

## House style

- Dates in ISO format: `YYYY-MM-DD`.
- One-line entries when possible. Link out for detail.
- Sign entries when the author is an agent: `— claude-foundation-opus47`.
