# docs/ — long-form documentation

What lives here:

- [`api-contract.md`](api-contract.md) — the stable wire contract between
  the Django backend and the React frontend. Endpoint paths,
  request/response shapes, error codes, ordering/search/pagination rules.
- [`threat-model.md`](threat-model.md) — STRIDE threat model per endpoint
  + supply-chain / logging / privacy sections. The security source of
  truth alongside [`SECURITY.md`](../SECURITY.md).
- [`extensions.md`](extensions.md) — how consumers extend the UI without
  writing React (`register_field_type`, the per-model panel hook).
- [`data-layer.md`](data-layer.md) — the `@dar/data` one-way data-flow
  rules (the only package that talks to `@dar/api`).
- [`ux/`](ux/) — the UX contract the SPA implements: principles,
  navigation, primary flows, responsive, theming, accessibility, PWA,
  loading/error states.
- [`consumer/`](consumer/) — real-adopter feedback + pilot requirements
  (input that drives the roadmap; **not** a usage guide).
- [`screenshots/`](screenshots/) — UI screenshots embedded in the README.
- [`agents/`](agents/) — durable inter-agent coordination artifacts:
  - [`decisions.md`](agents/decisions.md) — append-only log of accepted
    architectural decisions.
  - [`open-questions.md`](agents/open-questions.md) — questions awaiting
    resolution.
  - [`pr-workflow.md`](agents/pr-workflow.md) — the author/reviewer/merger
    protocol for autonomous PR ops.
  - [`autonomy-policy.md`](agents/autonomy-policy.md) — tier rules + kill
    switches governing what may be auto-merged vs. human-gated.
  - Per-role subteam docs live under `agents/` (product-manager,
    security-expert, software-architect, consumer).

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

- `installation.md` — deep-dive install + customization guide (the
  [README](../README.md) quickstart is the current entry point).
- `release.md` — the release procedure (gated by repo owner; see
  [`SECURITY.md`](../SECURITY.md) §6–§7 for the current gated process).
