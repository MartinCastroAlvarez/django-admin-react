# Architect review — PR #28 `chore/move-agents-to-docs-agents`

Posted: 2026-05-26
Reviewer: `claude-architect` (Software Architect / Engineering Lead)
PR branch: `chore/move-agents-to-docs-agents`
Tip commit: `38da4f9 refactor: move agents/ into docs/agents/ — single home for agent state`
Author: `MartinCastroAlvarez`

Per the 3-reviewer rule
([`docs/agents/decisions.md`](../docs/agents/decisions.md)), this is the
Architect role-specific review.

---

## Scope I checked

- Directory rename: top-level `agents/` → `docs/agents/` so that all
  agent durable state lives under a single `docs/agents/` root.
- 45 files changed: 30 markdown files (renames + reference rewrites) +
  3 code-adjacent files (`tests/test_security.py`,
  `.pre-commit-config.yaml`, `scripts/audit-deps.sh`) + several
  cross-doc reference fixes (`SECURITY.md`, `ARCHITECTURE.md`,
  `ACCEPTANCE.md`, `API_CONTRACT.md`, `CONTRIBUTING.md`, `ROADMAP.md`,
  `TESTING.md`, `docs/README.md`, `docs/ux/*`, `docs/pm-*`,
  `docs/screenshots/README.md`).
- Verified diff via `gh pr diff 28 --name-only` and
  `git diff --name-status --find-renames origin/main..pr28`.
- Verified no protected runtime / dep files touched.
- Verified test suite parity vs `main`.

## Findings

### 1. Git rename detection is intact (✅)
`git diff --find-renames origin/main..pr28` reports the role-folder
files at R077–R100 similarity (e.g.,
`R100 agents/security-expert/SKILLS.md → docs/agents/security-expert/SKILLS.md`,
`R077 agents/software-architect/STATUS.md → docs/agents/software-architect/STATUS.md`).
The three `agents/{DECISIONS,OPEN_QUESTIONS,README}.md` files show as
`D` because their content was merged into the existing
`docs/agents/{decisions,open-questions,README}.md` siblings rather than
moved verbatim — that is the correct call (no duplicate roots) and
explained by the matching `M` entries on those targets. History
followability via `git log --follow` is preserved for the renamed
files.

### 2. `tests/test_security.py` change is minimal and correct (✅)
The `DOC_PATHS` tuple drops the now-redundant
`"agents/security-expert/"` entry. The remaining `"docs/agents/"`
prefix already covers every role subfolder (including
`docs/agents/security-expert/`), so the allowlist semantics are
preserved exactly. The accompanying comment update reflects the new
single-prefix rationale. No new entries added; no entries removed
that aren't strictly subsumed by an existing entry. Test S37 still
passes locally.

### 3. `.pre-commit-config.yaml` and `scripts/audit-deps.sh` are pure
comment updates (✅)
Both files only adjust the path inside header comments
(`agents/security-expert/REVIEW_CHECKLIST.md` →
`docs/agents/security-expert/REVIEW_CHECKLIST.md`,
`agents/security-expert/NEXT_STEPS.md` →
`docs/agents/security-expert/NEXT_STEPS.md`). Hook ids, hook
commands, regex patterns, and shell logic are byte-identical.

### 4. `SECURITY.md` change is reference-only (✅)
The two changed lines in `SECURITY.md` §10 "See also" only rewrite
the two `agents/security-expert/*` links to `docs/agents/security-expert/*`.
No normative security policy, threshold, denylist, or rule is
touched. Tier escalation for `SECURITY.md` is therefore not
substantive — the file changed because its outbound links to moved
files had to follow. This is the minimum possible edit consistent
with the rename, and I would have rejected anything broader.

### 5. No bare `agents/` references remain (✅)
`gh pr diff 28 | grep -E '^\+.*[^/]agents/' | grep -v docs/agents/`
returns empty. Cross-doc references resolve.

### 6. No protected runtime surface touched (✅)
None of the following are in the diff:
`django_admin_react/`, `frontend/packages/`, `pyproject.toml`,
`package.json`, `.github/workflows/`, `LICENSE`,
`docs/api-contract.md`, `docs/agents/autonomy-policy.md`,
`docs/agents/pr-workflow.md`. URL patterns, serializer denylist,
CSRF / auth code, and dependency graphs are unchanged.

### 7. Test parity vs `main` (✅)
After `poetry install --no-root && poetry run pytest -q`:
`137 passed, 1 xfailed in 8.41s`. Matches `main` exactly. The xfail
is the pre-existing `test_s31_denylist_constant_exists_and_complete`
gated on PR #4. No new failures, no new flakes.

## Architectural concerns

- **None.** This PR is a pure structural cleanup: it eliminates the
  parallel top-level `agents/` root and consolidates everything under
  `docs/agents/`. It does not introduce a parallel permission /
  queryset / form system, does not add settings keys, does not change
  the URL surface, and respects the §2 Five Rules in `CLAUDE.md` in
  full.
- Folder discoverability improves: agent durable state and human-
  facing docs now share one tree, which simplifies the
  "every-folder-has-a-README" invariant.

## Risks

- **Low.** Documentation + state + comment-only changes.
- Outstanding orphan-link risk: any external doc (e.g., on a wiki or
  in a closed branch) that links to a `https://github.com/.../tree/main/agents/...`
  URL will 404. Mitigation is out-of-scope for this PR; the in-repo
  references all resolve.
- No backout risk: the move is fully reversible via `git revert`
  because every change is a rename or a path-string edit; nothing
  imports from `agents/`.

## Verdict

**Approve.**

This PR is a clean, minimal directory consolidation. The three
non-doc files (`tests/test_security.py`, `.pre-commit-config.yaml`,
`scripts/audit-deps.sh`) are touched only to the extent required by
the rename and preserve all logic. `SECURITY.md` changes are link
updates only, with no policy delta. Tests are green at the same
137 passed + 1 xfail as `main`. No architectural regressions; the
§2 Five Rules are preserved intact.

Recommend Merger: land this PR once Security and PM forum approvals
are in.

— `claude-architect`
