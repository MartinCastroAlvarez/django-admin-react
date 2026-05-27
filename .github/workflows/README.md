# `.github/workflows/`

GitHub Actions workflows for django-admin-react.

## What lives here

- **`ci.yml`** — the lint + test gate on every PR and push to `main`:
  backend (`scripts/lint.sh` → ruff/black/isort/flake8/pylint/mypy/bandit
  + the pre-commit security hooks + `pytest`) and frontend
  (`pnpm -r typecheck`, `pnpm lint`, `pnpm test`, `pnpm -r build`). A red
  suite blocks merge. Added in #452 (reversing the prior local-only
  posture). Marking the checks **required** is an owner branch-protection
  action (#452 / #331).
- **`codeql.yml`** — CodeQL static analysis (Python + JS/TS) on push/PR and a
  weekly schedule. This is the project's security dataflow scanner.
- **`release.yml`** — automated PyPI publishing. Triggered when a GitHub
  Release is **published** (a human authorises every release; the Release
  notes are the changelog entry), or manually via `workflow_dispatch` for a
  TestPyPI dry-run. Uses **PyPI Trusted Publishing (OIDC)** — no stored
  long-lived token — and SHA-pinned actions. See the header comment in the
  file for the one-time PyPI + GitHub-environment setup the owner must do
  before the first publish.

## What does not belong here

- The *definition* of the quality gate. `ci.yml` does not duplicate the
  tool list — the backend job runs `scripts/lint.sh` and the frontend job
  runs the package.json scripts, so the gate has one source of truth. See
  `SECURITY.md` §8 for the local + CI posture and #331 for the forward
  hardening plan (SHA-pinning is already done; required-checks /
  version-matrix remain).
- Secrets. Workflows authenticate via OIDC (release) or the default
  `GITHUB_TOKEN` (CodeQL). No long-lived tokens are stored as secrets.

## Pointers

- Release process + token/OIDC rationale: `SECURITY.md` §6–§7.
- Supply-chain / CI hardening roadmap: issue #331.
- Build pipeline the release workflow runs: `scripts/build.sh`.
