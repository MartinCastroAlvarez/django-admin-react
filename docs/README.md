# docs/ — long-form documentation

What lives here:

- [`api-contract.md`](api-contract.md) — the stable contract between the
  Django backend and the React frontend. Endpoint paths, request/response
  shapes, error codes, ordering/search/pagination rules.
- [`agents/`](agents/) — durable inter-agent coordination artifacts:
  - [`decisions.md`](agents/decisions.md) — append-only log of accepted
    architectural decisions.
  - [`open-questions.md`](agents/open-questions.md) — questions awaiting
    resolution.

What does **not** belong here:

- Status / progress / changelog data — that lives on the
  [Project board](https://github.com/users/MartinCastroAlvarez/projects/3),
  in the [Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues)
  list, and as merged PR history.
- Announcements / Q&A / community chatter — that goes in
  [GitHub Discussions](https://github.com/MartinCastroAlvarez/django-admin-react/discussions).
- Per-PR review conversation — that goes on the PR itself.
- Code or configuration — those live in their own directories.
- Folder READMEs — each folder owns its own.
- Secrets, tokens, or anything sensitive. This directory is committed
  and public.

Future docs (added when their PRs land):

- `installation.md` — deep-dive install + customization guide.
- `release.md` — the release procedure (gated by repo owner).
- `screenshots/` — UI screenshots for the README.
