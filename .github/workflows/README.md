# `.github/workflows/`

GitHub Actions workflows for django-admin-react.

## What lives here

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

- The local quality gate (`ruff`/`black`/`bandit`/`pytest`/`pnpm lint`) lives
  in `scripts/lint.sh` and `.pre-commit-config.yaml`, not in CI — see
  `SECURITY.md` §8 for the (deliberately) local-only posture and issue #331
  for the forward CI-hardening plan.
- Secrets. Workflows authenticate via OIDC (release) or the default
  `GITHUB_TOKEN` (CodeQL). No long-lived tokens are stored as secrets.

## Pointers

- Release process + token/OIDC rationale: `SECURITY.md` §6–§7.
- Supply-chain / CI hardening roadmap: issue #331.
- Build pipeline the release workflow runs: `scripts/build.sh`.
