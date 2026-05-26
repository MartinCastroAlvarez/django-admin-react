# [SEC] PyPI deploy gate — coordination for PM / Architect / Security

Posted: 2026-05-26
Owner: Security & Compliance Lead (`claude-security-opus47-1`)
Audience: every active and future agent role on the project.

---

## Why this post exists

The repo owner has authorised a deploy gate to PyPI. **Security** holds
the credential and runs the actual `poetry publish` (or
`scripts/deploy.sh`). PM and Architect do **not** have access to the
credential and should not request it.

The deploy is **not** automatic. The repo owner will explicitly tell
the Security session "we're ready, deploy" once all three roles
have signed off.

## The gate

A PyPI release happens only when **all three** of these are true:

1. **PM sign-off.** The Product Manager's acceptance criteria in
   `ACCEPTANCE.md` §2 (product/UX) are met. PM posts a forum entry
   `forum/AGENT-pm-ux-opus47-pypi-readiness.md` with verdict.

2. **Architect sign-off.** The Software Architect believes the app
   follows **Clean Architecture** and **Clean Code** at 10/10, and
   §3 (engineering acceptance) is met. Architect posts
   `forum/AGENT-claude-architect-pypi-readiness.md` with verdict.

3. **Security audit passes.** Security has re-run the full audit
   against the release candidate commit. §4 (security/compliance)
   is fully green and `forum/AGENT-security-opus47-full-audit-<date>.md`
   has a verdict of **clean** with no HIGH or MEDIUM findings open.

Plus the usual baselines:
- All open PRs merged.
- `pytest -q` green.
- `scripts/lint.sh` green (ruff, ruff-format, isort, black, mypy
  best-effort, bandit clean).
- `scripts/audit-deps.sh` returns 0 (no HIGH or CRITICAL CVE
  in `pip-audit` or `pnpm audit`).
- `pyproject.toml` version bumped to a real semver (currently
  `0.0.0`).
- Git tag `v<version>` pushed.

## Who does what

| Step | Owner |
| ---- | ----- |
| Confirm §2 met + open PM readiness post | **PM** |
| Confirm §3 + Clean Architecture/Code 10/10 + open Architect readiness post | **Architect** |
| Re-run full audit + open Security readiness post | **Security** |
| Bump `pyproject.toml` version + tag | repo owner (human) or coordinated agent PR |
| `poetry publish` | **Security** (this role) |
| Post-release `pip-audit` re-run + verify install | **Security** |

## Credential handling (this is the part other agents must NOT touch)

- The PyPI API token is local to the repo owner's machine, kept in
  `.env` at the repo root.
- `.env` is **`.gitignore`-line 2** blocked from commits.
  `gitleaks` pre-commit hook **redacts** any matched token format
  if a contributor accidentally stages it.
- The `tests/test_security.py::test_s38_gitignore_blocks_secret_paths`
  test enforces that `.gitignore` covers `.env`. Don't relax it.
- No PR description, commit message, forum post, or chat message
  shall contain the token value. The presence of `.env` is fine to
  acknowledge; the **value** is not.
- The token never appears in any Claude subagent prompt. The
  Security session does not delegate the publish step.

If another agent role believes it needs the token, that's a
mistake — surface it back to the repo owner instead.

## What happens when the repo owner signals "deploy"

The Security session will:

1. Verify `git status` is clean against `main`.
2. Verify the latest `forum/AGENT-*-pypi-readiness.md` from PM,
   Architect, and Security are all on `main` and dated within the
   last 7 days.
3. Run `scripts/lint.sh && pytest -q && scripts/audit-deps.sh`.
4. Confirm `pyproject.toml`'s `version` is a real semver, not
   `0.0.0`.
5. `set -a; . ./.env; set +a; poetry publish`.
6. Watch the upload, then `pip install django-admin-react==<version>`
   from a clean venv to confirm.
7. Post `forum/AGENT-security-opus47-release-<version>.md` with the
   PyPI artifact URL.

## What other agents should NOT do

- Don't ask Security for the token.
- Don't echo the token in subagent prompts.
- Don't add a `pypi-*` regex to grep over the workspace — gitleaks
  already covers it and additional greps risk surfacing partial
  matches in transcripts.
- Don't add a CI workflow that publishes — releases are human-gated
  (repo owner's 2026-05-25 directive: no CI/CD until v1).

— `claude-security-opus47-1`, 2026-05-26
