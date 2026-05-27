# Architect — open questions

> Open architectural questions awaiting a decision. When answered,
> append a one-line summary to
> [`DECISIONS.md`](DECISIONS.md) **and** to
> [`docs/agents/decisions.md`](../../docs/agents/decisions.md) (if
> cross-role), then delete the question here.

---

## OQ-A-002 — `API_CONTRACT.md` location

- **Opened**: 2026-05-25.
- **Owner**: Architect.
- **Question**: The role spec says to maintain `API_CONTRACT.md`. The
  actual contract is already at `docs/api-contract.md`. Two options:
  (a) move the canonical file to the repo root as `API_CONTRACT.md`;
  (b) keep it at `docs/api-contract.md` and add a thin pointer
  `API_CONTRACT.md` at the root.
- **Default assumption** (per [`ACCEPTANCE.md`](../../ACCEPTANCE.md)
  §3.9 Doc-A): option (b) is acceptable. The user-visible repo root
  has the pointer; the long-form contract stays under `docs/`.
- **Resolution path**: write a one-line `API_CONTRACT.md` at the root
  pointing at `docs/api-contract.md`. Track as a NEXT_STEP item.

## OQ-A-003 — `TESTING.md` scope

- **Opened**: 2026-05-25.
- **Owner**: Architect.
- **Question**: `TESTING.md` is referenced by `ACCEPTANCE.md` §3.5
  but not yet written. Should it duplicate `CLAUDE.md` §6 (test
  minimums) and `SECURITY.md` §4 (security tests), or should it stay
  light and link?
- **Default assumption**: stay light + link. `TESTING.md` documents
  the test layout (`tests/`, `tests/test_project/`, `tests/perf/`,
  `tests/e2e/`, `examples/*/tests/`), the runner commands, the fake-
  timer / fixture conventions, and links to the matrices instead of
  duplicating them.
- **Resolution path**: write `TESTING.md` in the follow-up PR.

## OQ-A-004 — Lint-pipeline scope creep

- **Opened**: 2026-05-25.
- **Owner**: Architect.
- **Question**: `scripts/lint.sh` currently runs nine Python tools.
  Adding `radon` (cyclomatic complexity, §3.12 MT-3) and a markdown
  link checker (`lychee` or `markdown-link-check`, §3.9 Doc-E) brings
  the count to eleven. At what point does the runtime become a real
  friction?
- **Default assumption**: ≤ 30 seconds wall-time is acceptable for
  the gate. If we cross that, we add `LINT_FAST=1` to skip the slow
  tools (mypy, pylint full).
- **Resolution path**: measure and decide when the additions land.

## OQ-A-005 — Frontend dependency budget

- **Opened**: 2026-05-25.
- **Owner**: Architect.
- **Question**: What's the dependency budget for `@dar/ui`? React +
  Tailwind are non-negotiable. Beyond that, every new dep is a
  forever-debt for a generic primitives package.
- **Default assumption**: zero new direct dependencies in `@dar/ui`
  besides React + Tailwind. Anything else (`@radix-ui/*`,
  `react-aria`, etc.) requires a decisions-log entry and PM/UX
  sign-off.
- **Resolution path**: enforce via §3.3 M-6; revisit if PM/UX flags
  an unmet accessibility need.

---

> Append new questions above this line. Keep each entry under ~200
> words. If the question needs cross-role input, mirror it to
> [`docs/agents/open-questions.md`](../../docs/agents/open-questions.md).
