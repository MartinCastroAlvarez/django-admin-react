# docs/ — long-form documentation

What lives here:

- [`api-contract.md`](api-contract.md) — the stable contract between the
  Django backend and the React frontend. Endpoint paths, request/response
  shapes, error codes, ordering/search/pagination rules.
- [`docs/agents/`](docs/agents/) — durable inter-agent coordination artifacts:
  - [`decisions.md`](docs/agents/decisions.md) — append-only log of accepted
    architectural decisions.
  - [`open-questions.md`](docs/agents/open-questions.md) — questions awaiting
    resolution.
  - [`changelog.md`](docs/agents/changelog.md) — one-line summaries of
    meaningful repo changes.

What does **not** belong here:

- Ephemeral coordination chatter — that goes in [`/forum/`](../forum/).
- Code or configuration — those live in their own directories.
- Folder READMEs — each folder owns its own.
- Secrets, tokens, or anything sensitive. This directory is committed
  and public.

Future docs (added when their PRs land):

- `installation.md` — deep-dive install + customization guide.
- `release.md` — the release procedure (gated by repo owner).
- `screenshots/` — UI screenshots for the README.
