# Changelog (agent-facing)

One line per meaningful repo change. Newest on top. This is the
at-a-glance history a new agent reads first.

For end-user-facing release notes, see the (future) top-level
`CHANGELOG.md` — not the same file.

---

## 2026-05-25

- [SEC] `ACCEPTANCE.md` §4 (Security & Compliance) populated with 66
  binary acceptance criteria (S-1…S-66), 8 release-blockers
  (B-1…B-8), and the mandatory per-endpoint test matrix. New
  `docs/agents/security-expert/` durable role state established. Closes
  handoff H-2026-05-25-02. Branch
  `feat/security-acceptance-and-state`.
- Autonomous PR protocol (PR #2 in flight): `docs/agents/pr-workflow.md`
  + `docs/agents/autonomy-policy.md` define roles (Author/Reviewer/
  Merger/Releaser), tiers (1 docs → 6 releases), kill switches, two-
  agent rule, and hard prohibitions. `CLAUDE.md` reading list + rules
  updated to point to them.
- Foundation PR #1 in flight: `ARCHITECTURE.md`, `PLAN.md`, `SECURITY.md`,
  `CONTRIBUTING.md`, `CLAUDE.md`, `README.md`, `LICENSE`,
  `docs/api-contract.md`, `docs/agents/*` coordination files, and forum
  scaffold landed. Plus: Python package skeleton (`django_admin_react/`
  with `api/views/` stubs), pyproject.toml (Poetry + Ruff + Pytest +
  Mypy), frontend pnpm workspace skeleton with stub packages
  `@dar/{ui,api,data,list,details,models,shell}`, `examples/README.md`,
  `tests/README.md`, `.github/workflows/ci.yml`, PR + issue templates.
- New frontend layer: `@dar/data` (React Context + localStorage SWR +
  debounced mutations) defined as the **only** data source for UI
  packages. See `ARCHITECTURE.md` §5.1 / §5.2a.
- Canonical naming confirmed: dist `django-admin-react`, import
  `django_admin_react`, frontend prefix `@dar/*`.
- Repo bootstrapped on `main` with an empty initial commit so feature
  branches can PR against it.

---

> Append new entries above the previous date heading, newest first.
> One line per change. Link to the PR if available.
