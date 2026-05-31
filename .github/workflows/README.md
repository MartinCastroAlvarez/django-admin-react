# `.github/workflows/`

GitHub Actions workflows for django-admin-react.

## What lives here

- **`ci.yml`** — the test gate on every PR and push to `main`: backend
  `pytest` (with coverage) and the frontend `pnpm` gate (`-r typecheck`,
  `lint`, `test`, `-r build`). A red suite blocks merge. Added in #452
  (reversing the prior local-only posture). The Python *lint* gate
  (`scripts/lint.sh`) is not in CI yet — it runs two formatters that
  conflict, so it's de-conflicted first (follow-up off #452). Marking the
  checks **required** is an owner branch-protection action (#452 / #331).
- **`codeql.yml`** — CodeQL static analysis (Python + JS/TS) on push/PR and a
  weekly schedule. This is the project's security dataflow scanner.
- **`publish.yml`** — automated PyPI publishing. Triggered when a GitHub
  Release is **published** (a human authorises every release; the Release
  notes are the changelog entry), or manually via `workflow_dispatch` for a
  TestPyPI dry-run. Uses **PyPI Trusted Publishing (OIDC)** — no stored
  long-lived token — and SHA-pinned actions. See the header comment in the
  file for the one-time PyPI + GitHub-environment setup the owner must do
  before the first publish.

## What does not belong here

- The Python *lint* gate (`scripts/lint.sh` + `.pre-commit-config.yaml`).
  CI runs `pytest` and the frontend `pnpm` gate; the Python lint gate
  isn't wired into CI yet (it must be de-conflicted first — two formatters
  disagree). See `SECURITY.md` §8 and #331 for the forward hardening plan
  (SHA-pinning is already done; lint-in-CI / required-checks /
  version-matrix remain).
- Secrets. Workflows authenticate via OIDC (release) or the default
  `GITHUB_TOKEN` (CodeQL). No long-lived tokens are stored as secrets.

## Pointers

- Release process + token/OIDC rationale: `SECURITY.md` §6–§7.
- Supply-chain / CI hardening roadmap: issue #331.
- Build pipeline the release workflow runs: `scripts/build.sh`.
