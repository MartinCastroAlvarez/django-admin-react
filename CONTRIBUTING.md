# Contributing to django-admin-react

Thank you for considering a contribution! This file explains the workflow
for humans. The companion file [`CLAUDE.md`](CLAUDE.md) lays out the same
contract for AI coding agents working in this repository.

## 1. Before you start

Read, in order:

1. [`README.md`](README.md)
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`SECURITY.md`](SECURITY.md)
4. [`docs/agents/decisions.md`](docs/agents/decisions.md) and
   [`docs/agents/open-questions.md`](docs/agents/open-questions.md)
5. The [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
   and open [Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues)
   for what's in flight and what's planned.

If anything you plan to do conflicts with those documents, open an
[Issue](https://github.com/MartinCastroAlvarez/django-admin-react/issues/new) or
a [Discussion](https://github.com/MartinCastroAlvarez/django-admin-react/discussions)
**before** writing code.

## 2. Development environment

```bash
# Python side
poetry install
poetry run pytest

# JS side (when the frontend lands in PR #6)
pnpm install
pnpm -r lint
pnpm -r typecheck
pnpm -r test
```

We use **Poetry** for Python and **pnpm** for JavaScript. Do not mix in
`pip install`, `npm`, or `yarn`.

### 2.1 Pre-commit hooks (recommended)

The repo ships a `.pre-commit-config.yaml` that runs `gitleaks` (secret
scan), `ruff`, `black`, `isort`, `bandit`, and a handful of local
`pygrep` rules that enforce `ACCEPTANCE.md` §4 invariants (no partial
token redactions, no `Model.objects.all/filter` in
`django_admin_react/api/`, no `@csrf_exempt` anywhere, no `user.has_perm`
in api code, no `@dar/api` imports from page packages).

To enable:

```bash
poetry run pip install pre-commit
pre-commit install
```

Every `git commit` now runs these hooks. If anything `[BLOCK]`s your
commit, fix the violation rather than disabling the hook. (See
`docs/agents/security-expert/REVIEW_CHECKLIST.md` for the rationale.)

If you skip pre-commit locally, `scripts/lint.sh` still runs the same
tools when the Merger gates your PR.

### 2.2 Dependency audit (release prep)

Run before any release tag:

```bash
./scripts/audit-deps.sh                 # default --fail-on=high
./scripts/audit-deps.sh --fail-on=critical   # release mode
```

This calls `poetry run pip-audit` and `pnpm audit --prod`. Any finding
at or above the threshold blocks the release per `ACCEPTANCE.md`
§4.9 S-44 / S-45.

## 3. Branching and PRs

- Branch from `main`.
- Branch naming: `feat/...`, `fix/...`, `docs/...`, `chore/...`,
  `refactor/...`, depending on the change type.
- Open one PR per branch. Multi-feature branches will be split.
- PR titles use Conventional Commits prefixes (`feat:`, `fix:`, `docs:`,
  `chore:`, `refactor:`, `test:`).
- The PR description must:
  - State what changed and why.
  - Link the driving [Issue](https://github.com/MartinCastroAlvarez/django-admin-react/issues)
    (`Closes #N`) and the matching
    [Project board](https://github.com/users/MartinCastroAlvarez/projects/3) card.
  - List which sections of [`ARCHITECTURE.md`](ARCHITECTURE.md) /
    `docs/` you updated.
  - Include the test matrix you ran (or "n/a, docs only").
- All review feedback and approvals happen as PR review comments — not
  as committed markdown files.
- Direct commits to `main` are reserved for the initial bootstrap commit.
  All real work goes through PRs.

## 4. Code style

- Python: `ruff format` and `ruff check --fix`. Type hints required on
  public functions.
- JavaScript / TypeScript: `eslint` + `prettier`. TypeScript everywhere;
  no plain `.js` in source.
- File-level docstrings explain *why*, not *what*. Inline comments only
  when the why is non-obvious.

## 5. Tests

- Python tests live in `tests/`. We use `pytest` with `pytest-django`.
- The minimum test matrix for every endpoint is in
  [`SECURITY.md`](SECURITY.md) §4.
- The frontend test setup will land in PR #6; details will be added then.

## 6. Documentation

- Every folder has a `README.md`. Adding a folder without one will block
  review.
- If you change architecture, update [`ARCHITECTURE.md`](ARCHITECTURE.md)
  in the same PR.
- If you change scope, update the driving Issue (or open a new one) and
  the relevant card on the
  [Project board](https://github.com/users/MartinCastroAlvarez/projects/3).
- Significant decisions get a one-line entry in
  [`docs/agents/decisions.md`](docs/agents/decisions.md).

## 7. Security

- Read [`SECURITY.md`](SECURITY.md).
- Never commit secrets. If you do by accident, see SECURITY §5.
- Vulnerability reports go through a private channel, not public issues.

## 8. Multi-agent coordination

Several AI agents may work on this repository concurrently. Coordination
happens through GitHub primitives — not committed markdown:

- **[Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues)**
  — work tracking. Claim an issue (assign yourself or post a comment)
  before starting.
- **[Project board](https://github.com/users/MartinCastroAlvarez/projects/3)**
  — Priority / Area / Phase across in-flight and planned work.
- **[Discussions](https://github.com/MartinCastroAlvarez/django-admin-react/discussions)**
  — announcements, Q&A, ideas, show-and-tell.
- **PR review comments** — all review feedback and all approvals.
  Never as committed markdown files.
- [`docs/agents/decisions.md`](docs/agents/decisions.md): append-only
  ADRs (one line each, link out for detail).
- [`docs/agents/open-questions.md`](docs/agents/open-questions.md):
  questions awaiting a decision that aren't yet shaped for an Issue or
  Discussion.

Everything in this repository (`docs/`, commits, PR descriptions, Issues,
Discussions) is public. **Do not paste secrets or private data anywhere.**

## 9. Releasing

Releases are gated. Only a repository owner with the PyPI token in hand can
trigger a publish. See [`SECURITY.md`](SECURITY.md) §6 and §7.

## 10. License

By contributing you agree to license your contribution under the MIT
license that covers this repository. See [`LICENSE`](LICENSE).
