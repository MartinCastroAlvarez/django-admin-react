# Contributing to django-admin-react

Thank you for considering a contribution! This file explains the workflow
for humans. The companion file [`CLAUDE.md`](CLAUDE.md) lays out the same
contract for AI coding agents working in this repository.

## 1. Before you start

Read, in order:

1. [`README.md`](README.md)
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`PLAN.md`](PLAN.md)
4. [`SECURITY.md`](SECURITY.md)
5. [`docs/agents/decisions.md`](docs/agents/decisions.md) and
   [`docs/agents/open-questions.md`](docs/agents/open-questions.md)

If anything you plan to do conflicts with those documents, open an issue or
add an entry to `docs/agents/open-questions.md` **before** writing code.

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

## 3. Branching and PRs

- Branch from `main`.
- Branch naming: `pr/<NN>-<short-kebab-slug>` for the planned PR sequence
  (see [`PLAN.md`](PLAN.md) §2), or `feat/...`, `fix/...`, `docs/...`,
  `chore/...` for everything else.
- Open one PR per branch. Multi-feature branches will be split.
- PR titles use Conventional Commits prefixes (`feat:`, `fix:`, `docs:`,
  `chore:`, `refactor:`, `test:`). The numbered foundation PRs may prepend
  `PR #NN —` for readability.
- The PR description must:
  - State what changed and why.
  - List which files in [`ARCHITECTURE.md`](ARCHITECTURE.md) /
    [`PLAN.md`](PLAN.md) / `docs/` you updated.
  - Include the test matrix you ran (or "n/a, docs only").
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
- If you change the plan or scope, update [`PLAN.md`](PLAN.md) in the same
  PR.
- Significant decisions get a one-line entry in
  [`docs/agents/decisions.md`](docs/agents/decisions.md).

## 7. Security

- Read [`SECURITY.md`](SECURITY.md).
- Never commit secrets. If you do by accident, see SECURITY §5.
- Vulnerability reports go through a private channel, not public issues.

## 8. Multi-agent coordination

Several AI agents may work on this repository concurrently. Coordination
happens through:

- [`docs/agents/decisions.md`](docs/agents/decisions.md): one-line entries
  for accepted architectural decisions. Append-only.
- [`docs/agents/open-questions.md`](docs/agents/open-questions.md):
  questions awaiting a decision. Anyone can append; once answered the
  question moves to `decisions.md`.
- [`docs/agents/changelog.md`](docs/agents/changelog.md): notable changes,
  one line per PR.
- [`forum/`](forum/): free-form discussion threads (one `.md` per topic).
  Use this for design conversation that does not yet belong in
  `decisions.md`.

Anything in `forum/` and `docs/agents/` is committed and public. **Do not
paste secrets or private data into those files.**

## 9. Releasing

Releases are gated. Only a repository owner with the PyPI token in hand can
trigger a publish. See [`SECURITY.md`](SECURITY.md) §6 and §7.

## 10. License

By contributing you agree to license your contribution under the MIT
license that covers this repository. See [`LICENSE`](LICENSE).
