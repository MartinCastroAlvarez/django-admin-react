# Autonomy policy

Open-source code is a permanent public record. This document defines
**exactly** what AI agents may merge autonomously, what requires a
human in the loop, and the kill switches that override agent
autonomy.

Read this together with [`pr-workflow.md`](pr-workflow.md) (the
mechanics) and [`../../SECURITY.md`](../../SECURITY.md) (what we
defend against and the guarantees we make).

---

## 1. Tiers

Every PR is classified by its **highest-tier touched file**. A
mixed PR is treated at the higher tier.

### Tier 1 — Docs only

**Includes:** `*.md` outside `SECURITY.md` / `LICENSE`, `docs/**`
(other than `docs/api-contract.md`), folder READMEs.

**Required reviewers:** 1 agent approve.
**Auto-merge:** yes, after CI green + checklist.

### Tier 2 — Skeletons / stubs / types

**Includes:**
- New empty `*.py` files with only docstrings.
- New empty TypeScript module re-exports.
- `.gitkeep`, `.editorconfig`, `.gitignore` additions (not deletions).
- New folders with READMEs.
- `tsconfig.json`, `vite.config.ts` files **as long as** they don't add
  network calls or env reads.

**Required reviewers:** 1 agent approve.
**Auto-merge:** yes, after CI green + checklist.

### Tier 3 — Backend implementation (non-security)

**Includes:** new logic under `django_admin_react/` that does not
touch authn, authz, CSRF, the serializer denylist, or the
`ModelAdmin` permission contract. Adding a new endpoint that follows
the existing pattern lives here.

**Required reviewers:** 2 agent approves, **at least one** must check
the `[S]`-marked items in `pr-workflow.md` §5.1.
**Auto-merge:** yes, after CI green + checklist + both approves.

### Tier 4 — Frontend implementation

**Includes:** new code under `frontend/packages/`, Tailwind config,
build pipeline changes that do **not** disable security plugins.

**Required reviewers:** 2 agent approves.
**Auto-merge:** yes, after CI green + checklist + both approves.

### Tier 5 — Security / contract surface — **human required**

**Includes any change to:**

- `SECURITY.md`
- `LICENSE`
- `docs/api-contract.md` (the wire contract is a public commitment)
- `docs/agents/autonomy-policy.md` (this file)
- `docs/agents/pr-workflow.md`
- `pyproject.toml` `[tool.poetry.dependencies]` /
  `[tool.poetry.group.dev.dependencies]` adds, bumps, or removes
- Frontend root `package.json` `dependencies` /
  `devDependencies` adds, bumps, or removes
- `.github/workflows/**` (workflow files)
- Any file that imports / configures CSRF, session, login, or
  `ModelAdmin.has_*_permission`
- The serializer's sensitive-field denylist
- `django_admin_react/conf.py` defaults (changes settings semantics
  for every consumer)
- New URL patterns that mount publicly (`urls.py` top-level adds)

**Auto-merge:** **no.** A human must approve via GitHub UI.

### Tier 6 — Releases

**Includes:** version tag in `pyproject.toml`, git tag push,
publish to prod PyPI.

**Auto-merge:** **no.** Human required at every step, including
holding the PyPI API token.

Agents may publish to **TestPyPI** for verification only if a human
explicitly triggers the workflow.

---

## 2. The two-agent rule

For tiers 3 and 4:

- **Author ≠ Reviewer.** Different `agent-id` claims, different
  sessions.
- **Author ≠ Merger.** The session that opens the PR cannot be the
  session that merges it.
- **Reviewers may share an agent-id across PRs** but not within a PR
  (no double-counting one agent's two reviews).
- **One vote per session, per PR.**

A human counts as any number of agent approves for the purpose of
auto-merge; one human approval is sufficient for any tier ≤4 even if
no agents reviewed.

---

## 3. Kill switches

Any of these immediately disables autonomous merging until a human
re-enables:

1. **File `KILL_SWITCH` exists at the repo root.** Any agent finding
   this file aborts merge attempts and posts a comment on the most
   recent open PR (or opens an issue if none). The file contents may
   include the reason.
2. **`docs/agents/autonomy-policy.md` has been edited in the last 24
   hours.** Until a human reviews + this change merges, agents fall
   back to "human approval required for everything".
3. **Two failed CI runs back-to-back on `main`.** Agents pause auto-
   merge and notify the human.
4. **Open issue labelled `incident:secret-leak` or `incident:*`.**
   Any active incident issue disables autonomy. Close the issue (with
   a remediation summary) to re-enable.

To **manually** disable: `touch KILL_SWITCH && git add KILL_SWITCH &&
git commit -m "chore: disable agent autonomy" && git push`.
To re-enable: remove the file via PR (yes, even that PR is gated).

---

## 4. Hard prohibitions (no exceptions, ever)

Agents must **never**:

- `git push --force` to any branch other than their own personal
  feature branch, and even then only with explicit human consent.
- Force-push to `main`. Ever. Even after a leak — that's a human
  decision.
- Delete `main` or any protected branch.
- Disable a CI job, security check, or required review to land a PR.
- Add `# noqa`, `# type: ignore`, or `eslint-disable` on a
  security-relevant rule.
- Skip / xfail a security test without a linked GitHub issue and
  human approval.
- Bypass branch protection.
- Publish to prod PyPI.
- Add a new third-party dependency without a `decisions.md` entry.
- Touch `LICENSE`, `SECURITY.md`, or this file without human review.
- Echo a token, secret, `.env` content, or `git config` output into
  any committed file (docs, PR body, commit message, Issue,
  Discussion).
- Resolve a merge conflict by overwriting another agent's change
  silently.
- Modify the gh CLI auth state, `git config`, or `.git/hooks/`
  on the user's machine.

---

## 5. What "approved" means for an agent

An agent approval is **only** valid if all of these are true:

- The reviewer session is a different `agent-id` than any author or
  co-author of the diff.
- The reviewer ran the full `pr-workflow.md` §5.1 checklist and
  recorded the results as a PR review comment.
- The reviewer ran the local checks (or verified CI ran them) within
  the same session as the approval.
- The reviewer wrote a free-form reason for the approval (one
  sentence minimum). "LGTM" alone is rejected.

A Merger session may reject any approval that fails these criteria.

---

## 6. Audit trail

For every auto-merged PR, the Merger must leave behind, on the PR
itself (as the final close-out comment):

- PR number and title.
- List of agent-ids that approved + reviewer summary.
- Computed tier and why.
- CI run URL.
- Confirmation that §5.1 checklist passed.

The Merger also moves the linked
[Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
card to **Done** (and closes the driving issue if not already
auto-closed by `Closes #N`).

These artifacts — PR review comments + closed PR + closed issue +
moved card — are how a human auditor reconstructs *who decided what,
when, and why* without leaving GitHub.

---

## 7. Defaults if something is unclear

| Question                                          | Default                |
| ------------------------------------------------- | ---------------------- |
| Is this tier 3 or tier 5?                         | Higher tier (5).       |
| Do I count this approval?                         | No, if any doubt.      |
| Is CI flaky or actually failing?                  | Treat as failing.      |
| Should I auto-resolve this conflict?              | No — open a question.  |
| Does this change touch security?                  | Assume yes if unsure.  |
| Can I publish a release because tests pass?       | No. Human always.      |

When in doubt, **err human**.

---

## 8. Re-evaluation

This file is reviewed on a rolling basis:

- After every tier 5 PR.
- After any incident (closed `incident:*`-labelled issue).
- Before the first PyPI release (revisit tier 6 / release process).
- Every 30 days of active development.

Re-evaluation is itself a tier 5 change — it requires human approval.
