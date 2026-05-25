# Architect — next steps

> The single source of truth for what to do next. If you are a fresh
> session, **start at the top of the list and verify each item is
> still applicable** before acting (`git log`, `gh pr list`).

---

## Immediate (this PR / next merge cycle)

- [x] Write `ACCEPTANCE.md` §3 (engineering acceptance criteria).
- [x] Create `agents/software-architect/` durable state files.
- [x] Create shared `agents/{DECISIONS,OPEN_QUESTIONS,HANDOFF}.md`
      stubs.
- [ ] Run `./scripts/lint.sh` locally if any code changed
      (markdown-only PR → skip lint; record decision in STATUS).
- [ ] Commit, push, open PR (base `main`, head
      `feat/acceptance-criteria-engineering`).
- [ ] After merge: append a one-liner to
      `docs/agents/changelog.md` in the next chore PR, and update
      `PROGRESS.md` (`ACCEPTANCE.md` §3 row → ✅).

## Short-term (≤ 3 PRs after this one)

- [ ] **`TESTING.md`** at repo root (links into `CLAUDE.md` §6 and
      `SECURITY.md` §4 rather than duplicating). Cross-references
      `ACCEPTANCE.md` §3.5.
- [ ] **`API_CONTRACT.md`** at repo root — thin pointer to
      `docs/api-contract.md`. Aligns with §3.9 Doc-A and the role
      spec's required-file list.
- [ ] Add `radon` and a markdown link checker to
      `pyproject.toml` dev deps + wire them into `scripts/lint.sh`.
      Enables enforcement of §3.12 MT-3 and §3.9 Doc-E.
- [ ] Enable `pytest-randomly` (or `pytest -p randomly`) by adding
      `pytest-randomly` to dev deps and the test command. Required
      by §3.5 T-3.

## Medium-term (post-`0.1.0rc` planning)

- [ ] Re-enable `.github/workflows/ci.yml` (was dropped per repo
      owner). Resolution criterion in `OPEN_QUESTIONS.md` OQ-A-001.
- [ ] Add `pip-audit` and `pnpm audit` to `scripts/lint.sh` (or a
      sibling `scripts/audit.sh`) so §3.7 Q-3 becomes a one-command
      check.
- [ ] Add `lychee` (or `markdown-link-check`) to `scripts/lint.sh`
      so §3.9 Doc-E becomes enforceable.
- [ ] Add an explicit `pytest-benchmark` suite under `tests/perf/`
      and document the budgets in `TESTING.md`. Required by §3.5
      T-7 before tagging `0.1.0`.

## Engineering PRs (per `PLAN.md` §2, not yet merged)

- [ ] **PR #4 backend list/detail** —
      `GET /api/v1/<app>/<model>/` + `GET /api/v1/<app>/<model>/<pk>/`.
      Author claim is held by another session
      (`claude-author-opus47-pr03`), confirm via
      `gh pr list` before claiming.
- [ ] **PR #5 backend writes** — `POST` / `PATCH` / `DELETE`.
      Requires the form + serializer contract to be stable; design
      review in the PR body.
- [ ] **PR #6 frontend shell** — pnpm workspace, `@dar/ui`,
      `@dar/api`, `@dar/data`, `@dar/shell`, eslint rule that
      forbids `@dar/api` imports from page packages.
- [ ] **PR #7 frontend pages** — `@dar/list`, `@dar/details`,
      `@dar/models`. Tests per §3.5 T-8.
- [ ] **PR #8 examples wired up + screenshots** — replace
      `README.md` ASCII mockups with real screenshots. Required by
      `ACCEPTANCE.md` §2.3 O-2 (PM-owned) and §3.5 T-5 (E2E).

## Long-term / blockers

- [ ] First PyPI release (`0.1.0`). Tier 6; human-only. The
      Architect's responsibility is to ensure §3.13 is green before
      handing off; the PM and Security agents own their respective
      checklists.

---

## How to claim an item

1. `git fetch origin && gh pr list --state open` to confirm no other
   agent is on it.
2. Open a forum claim
   `forum/AGENT-architect-<topic>-claim.md` with the scope.
3. Open a draft PR with `[WIP]` so other agents see your claim
   reflected on GitHub too.
4. Update [`STATUS.md`](STATUS.md) and this file.

## How to mark an item complete

1. Move the bullet from the relevant section into the **Done** log
   at the bottom of this file (oldest at bottom).
2. Append a one-liner to `docs/agents/changelog.md` in the same PR.
3. Update [`PROGRESS.md`](../../PROGRESS.md) if it represents a
   milestone.

---

## Done log

- 2026-05-25 — Wrote `ACCEPTANCE.md` §3 (engineering acceptance
  criteria). Bootstrapped `agents/software-architect/` durable state.
