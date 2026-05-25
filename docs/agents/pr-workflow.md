# Autonomous PR workflow for Claude agents

This document defines how Claude agents send, review, approve, merge,
and pull PRs in this repository **without human-in-the-loop on every
step**, while preserving open-source security guarantees.

> Read this together with [`autonomy-policy.md`](autonomy-policy.md)
> (what's auto-mergeable vs human-only) and [`../../SECURITY.md`](../../SECURITY.md).

> **Hard rule.** If any check in §5 fails, the PR is not auto-merged
> — full stop. Escalate to a human reviewer.

---

## 1. Roles

Each Claude session adopts exactly one of these roles when it starts:

| Role        | Picks up                                       | May call                                                     | May NOT call                                  |
| ----------- | ---------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------- |
| **Author**  | Next unclaimed PR in `PLAN.md` §2 + this doc   | `git push`, `gh pr create`, `gh pr edit`                     | `gh pr review`, `gh pr merge` on their own PR |
| **Reviewer** | Any PR in `open` state without a recent review | `gh pr review --comment / --request-changes / --approve`, `gh pr diff`, `git fetch && git checkout` | `gh pr merge` (only Merger may merge)         |
| **Merger**  | Any PR that meets §5 auto-merge criteria       | `gh pr merge --squash --delete-branch`, `gh pr close`        | bypass the §5 checklist                       |
| **Releaser**| Tagging a version and publishing to PyPI       | `gh release create`, `poetry publish` (TestPyPI only)        | publish to **prod PyPI** (always human-gated) |

Pick the role you'll play in your session's first `forum/` post. Don't
switch roles mid-PR — start a new session.

**No agent may take more than one role on the same PR.** If you wrote
the diff, you cannot also review or merge it.

---

## 2. Session start checklist (every Claude session)

Before any tool call:

1. Read `CLAUDE.md` (this file is referenced from there).
2. Read `PLAN.md`, `ARCHITECTURE.md`, `SECURITY.md`,
   `docs/agents/decisions.md`, `docs/agents/changelog.md`.
3. `git fetch origin && git status` to see local state.
4. `gh pr list --state open --json number,title,headRefName,labels`
   to see open PRs.
5. `ls forum/` to see active claims.
6. Pick your role; post a one-line forum claim.

If `gh` is not authed to the repo, **stop and tell the human**. Do not
try clever workarounds.

---

## 3. Author workflow

```
Session start  ──►  Pick a PR slot from PLAN.md §2 (or open-questions)
                ──►  forum claim posted
                ──►  git checkout -b pr-<NN>-<slug>  (or feat/<slug>)
                ──►  write code + tests + docs
                ──►  local checks (see §5.2)
                ──►  git push -u origin <branch>
                ──►  gh pr create  (HEREDOC body following template)
                ──►  forum status post + PLAN.md table update
                ──►  Author done. Do not review or merge your own PR.
```

### Author musts

- **One concern per PR.** If your branch grows past ~600 meaningful
  diff lines, split it.
- **Tests with the feature.** No "tests in a follow-up PR".
- **Docs in the same PR** as the behavior they describe.
- **Conventional commits.** `feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `test:`, `ci:`, `build:`, `perf:`.
- **Cite the contract.** Every PR body lists the `ARCHITECTURE.md` /
  `docs/api-contract.md` section(s) it implements.
- **No `--force` push.** If you need to rewrite history (e.g.,
  accidentally committed a secret — see §6), open a forum thread and
  wait for human approval.

### Author must nots

- Do not approve your own PR (even with a different agent id; one
  human = one author per PR).
- Do not merge your own PR.
- Do not push to `main`. Ever. The only exception is the one-time
  empty bootstrap commit already shipped.

---

## 4. Reviewer workflow

```
Session start  ──►  forum claim "reviewing PR #N"
                ──►  gh pr checkout N
                ──►  gh pr diff N | head -... (or read locally)
                ──►  Apply checklist §5.1
                ──►  Either:
                       gh pr review N --approve --body "<short reason>"
                     OR
                       gh pr review N --request-changes --body "..."
                     OR
                       gh pr review N --comment --body "..."  (questions)
                ──►  forum post with link to review and checklist results
```

### Reviewer musts

- Run the full §5.1 checklist. Don't skip items because "it's obvious".
- Quote specific file + line + reason for every requested change.
  Vague reviews don't count toward §5.3.
- **At least one** reviewer on every PR must check the security
  checklist (§5.1 items marked `[S]`). The forum post says which.
- Verify CI is green. If CI failed, request changes; do not approve.

### Reviewer must nots

- Don't approve PRs you co-authored or commented on as a co-designer.
- Don't approve PRs that disable / weaken a security rule, even if the
  author argues it's fine. Escalate to a human via
  `docs/agents/open-questions.md` and request changes.

---

## 5. The auto-merge gate

A PR may be auto-merged by a **Merger** session **only** if all of
these are true:

### 5.1 Review checklist (the Merger must verify each item)

For every PR:

- [ ] PR title follows Conventional Commits.
- [ ] PR description links the `ARCHITECTURE.md` / `docs/api-contract.md`
      section(s).
- [ ] CI is green (every job, including the secret scan).
- [ ] **[S]** No secrets, tokens, keys, PEMs, `.env` content, or
      `git config` output in the diff. Even partial / redacted tokens
      are blocked.
- [ ] **[S]** No `Model.objects.all()` added in `django_admin_react/`.
- [ ] **[S]** No `csrf_exempt`, `permission_classes = []`,
      `has_*_permission` weakening, or "TODO add auth" left in the
      diff.
- [ ] **[S]** No frontend imports of `@dar/api` from page packages
      (`@dar/list`, `@dar/details`, `@dar/models`, `@dar/shell`).
- [ ] **[S]** No model-specific names (`Account`, `Book`, …) in
      `django_admin_react/` or `frontend/packages/`.
- [ ] No `# noqa` on a security-relevant rule.
- [ ] No tests skipped / xfailed without an issue link.
- [ ] No new third-party Python dependency without an entry in
      `docs/agents/decisions.md`.
- [ ] No new third-party npm dependency in a generic package
      (`@dar/ui`, `@dar/api`, `@dar/data`) without a decisions entry.
- [ ] Docs touched if behavior changed (especially
      `docs/api-contract.md`).
- [ ] `PLAN.md` §2 status column updated.
- [ ] `docs/agents/changelog.md` has a one-liner for this PR.
- [ ] If the PR adds a new folder, that folder has a `README.md`.

### 5.2 Local-only Author checks (before opening PR)

- [ ] `poetry run pytest`
- [ ] `poetry run ruff check .`
- [ ] `poetry run ruff format --check .`
- [ ] If frontend changed: `pnpm -r lint && pnpm -r typecheck && pnpm -r build`
- [ ] `git diff --cached | grep -iE '(ghp_|gho_|ghs_|aws_secret|begin (rsa|ec|openssh) private)'`
      returns nothing.

### 5.3 Approval threshold (auto-merge tiers)

The required reviewer count and reviewer makeup depend on what the
PR touches. Authoritative tiering lives in
[`autonomy-policy.md`](autonomy-policy.md); the summary:

| Tier | Surface                                                                        | Reviewers required | Human required? |
| ---- | ------------------------------------------------------------------------------ | ------------------ | --------------- |
| 1    | Docs only (`docs/`, `*.md`), forum/, folder READMEs                            | 1 agent approve    | No              |
| 2    | Skeletons, stubs, type-only changes, READMEs touched alongside skeleton        | 1 agent approve    | No              |
| 3    | Backend code (`django_admin_react/`) without security surface change           | 2 agent approves   | No              |
| 4    | Frontend code under `frontend/packages/`                                       | 2 agent approves   | No              |
| 5    | **Any change to** `SECURITY.md`, `LICENSE`, dependencies (`pyproject.toml` deps, frontend root `package.json` deps), `.github/workflows/`, CSRF/permission code | n/a                | **Yes — human** |
| 6    | PyPI release (tag → publish)                                                   | n/a                | **Yes — human** + token |

A Merger must compute the PR's tier from its **highest-tier touched
file**. If a doc-only PR also touches `SECURITY.md`, it is tier 5.

### 5.4 Merge command

```
gh pr merge <N> --squash --delete-branch --subject "<conventional title>" --body ""
```

- **Squash** keeps `main` linear. No merge commits.
- **Delete-branch** keeps the remote tidy.
- After merge, the Merger:
  - Appends a one-liner to `docs/agents/changelog.md` (next PR will
    pick it up).
  - Marks the `PLAN.md` §2 row "Merged".
  - Posts a final forum status close-out.

---

## 6. When something goes wrong

### Secret accidentally committed

1. Whoever notices it: **stop**. Do not push more commits.
2. Post a `forum/INCIDENT-<date>-secret-leak.md`.
3. Rotate the secret on the upstream provider (GitHub, AWS, etc.).
4. Wait for explicit human approval before history rewrite. No
   agent may `git push --force` autonomously, ever.

### CI is red but you think it's flaky

- Re-run **once**. If it still fails, request changes. No "merge
  through red".
- Never disable a security CI job to make a merge happen.

### A reviewer requests changes you disagree with

- Don't dismiss the review. Either:
  - Make the change and force-push **with the reviewer's consent**, or
  - Open a `docs/agents/open-questions.md` entry and pause the PR.

### Two agents racing on the same PR

- First `forum/` claim wins. The loser posts a counter-claim or picks
  another PR.
- Never rebase another agent's branch without their consent.

### The merge gate is ambiguous (e.g., is this tier 3 or tier 5?)

- Default to the **higher** tier. Err toward human review.
- File an open question; let the next round of agents codify it.

---

## 7. Pulling other agents' work

When a PR you depend on merges:

```
git fetch origin
git checkout main && git pull --ff-only
git checkout <your-branch>
git rebase main           # not merge — keeps history linear
# resolve conflicts; rerun §5.2; push
```

If a conflict touches a security-relevant file (see tier 5), do not
auto-resolve. Open an `open-questions.md` entry and pause.

---

## 8. What never goes through this protocol

- Releases to **prod PyPI**. Human + token in hand, always.
- Force-push to `main`. Never. Even with human approval, prefer revert
  commits.
- Adding a new GitHub Actions workflow. Tier 5 — human review.
- Changing `LICENSE`. Tier 5.
- Granting another GitHub account write access. Out of scope for
  agents.
- Modifying `.github/workflows/*` or `pyproject.toml`'s build backend.

---

## 9. Quick reference

```
# Open a PR
gh pr create --base main --head <branch> --title "<conv: subject>" --body-file pr-body.md

# Find PRs needing review
gh pr list --state open --search "no:approved -review-requested:@me"

# Check out and review
gh pr checkout <N>
gh pr diff <N>
gh pr review <N> --approve --body "..."         # or --request-changes / --comment

# Auto-merge (after §5 passes)
gh pr merge <N> --squash --delete-branch

# Pull main + rebase your branch
git fetch origin && git rebase origin/main
```

---

## 10. Cross-references

- [`autonomy-policy.md`](autonomy-policy.md) — tier rules, what's
  human-only, kill switches.
- [`../../SECURITY.md`](../../SECURITY.md) — the security guarantees
  every reviewer must enforce.
- [`../../CLAUDE.md`](../../CLAUDE.md) — top-level agent rules.
- [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) — human-facing
  workflow (mostly the same; humans skip the §1 role gating).
