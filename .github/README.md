# `.github/`

GitHub-specific templates and config for `django-admin-react`.

## What lives here

- `ISSUE_TEMPLATE/` — bug + enhancement forms surfaced by GitHub's
  "New issue" picker. `config.yml` disables the blank-issue path and
  routes security reports + general questions out to the right
  surface (Security Advisory + Discussions respectively).
- `PULL_REQUEST_TEMPLATE.md` — default PR body for new PRs, baking
  in the role-declaration + contract-citation pattern the
  [`docs/agents/autonomy-policy.md`](../docs/agents/autonomy-policy.md)
  workflow expects.

## What does NOT belong here

- **CI workflows** — none exist by design (`SECURITY.md` §8 — local
  checks via `./scripts/lint.sh` are the gate; no CI in v0.x).
  Adding any file under `.github/workflows/` is Tier 5 and requires
  human review per
  [`docs/agents/autonomy-policy.md`](../docs/agents/autonomy-policy.md)
  §1.5.
- **Funding / sponsor metadata** — out of scope for v0.x.

## Pointers

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — human-author workflow.
- [`../docs/agents/pr-workflow.md`](../docs/agents/pr-workflow.md) —
  agent-author workflow.
- [`../SECURITY.md`](../SECURITY.md) §1 — security reporting
  protocol (referenced by `ISSUE_TEMPLATE/config.yml`).
