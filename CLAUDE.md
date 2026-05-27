# CLAUDE.md

This file is the contract between this repository and any Claude (or other
AI) agent contributing to it. **Read this file from top to bottom before
doing anything else, every session.** Multiple agents may be working
concurrently — coordination is the only way to avoid stepping on each
other.

> If anything in this file is unclear or seems wrong, do **not** silently
> work around it. Add an entry to
> [`docs/agents/open-questions.md`](docs/agents/open-questions.md) and pick
> the simpler interpretation.

---

## 0. Required reading on session start

Read these, in order, every session:

1. [`CLAUDE.md`](CLAUDE.md) — this file. Check for updates since last
   session.
2. **Live status: the [GitHub Projects board](https://github.com/users/MartinCastroAlvarez/projects/3)**
   ("django-admin-react roadmap"). What's in flight, what's blocked,
   what's planned, by Priority / Area / Phase. Claim a card before
   opening a PR.
3. **Open [Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues)** —
   the work backlog. The board surfaces them with priority/area; the
   issue itself carries the acceptance signal.
4. **Recent activity: [open](https://github.com/MartinCastroAlvarez/django-admin-react/pulls)
   and [closed PRs](https://github.com/MartinCastroAlvarez/django-admin-react/pulls?q=is%3Apr+is%3Aclosed)
   + [Discussions](https://github.com/MartinCastroAlvarez/django-admin-react/discussions)** —
   what other agents have shipped recently and announced.
5. [`ARCHITECTURE.md`](ARCHITECTURE.md) — the architectural contract.
6. [`SECURITY.md`](SECURITY.md) — non-negotiable security rules.
7. [`docs/agents/decisions.md`](docs/agents/decisions.md) — accepted
   decisions.
8. [`docs/agents/open-questions.md`](docs/agents/open-questions.md) —
   open questions; do not re-decide things already answered in
   `decisions.md`.
9. [`docs/agents/pr-workflow.md`](docs/agents/pr-workflow.md) — the
   author/reviewer/merger protocol for autonomous PR ops. **Pick your
   role for the session before any tool call.**
10. [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md)
    — tier rules and kill switches. Before merging anything, classify
    the PR by its highest-tier touched file.

If your session's task touches a specific folder, also read that folder's
`README.md`.

---

## 1. Mission summary

We are building an open-source Django package, **`django-admin-react`**,
that:

- Is installed with `pip install django-admin-react` and added to
  `INSTALLED_APPS`.
- Mounts at any URL the consumer chooses (e.g.,
  `path("admin-react/", include("django_admin_react.urls"))`).
- Serves a single-page React UI that replaces the HTML admin pages.
- Reuses the consumer's existing `ModelAdmin` classes as the **only**
  source of truth for permissions, querysets, forms, and field
  configuration.
- Reuses Django's session + CSRF for authentication. Defaults to
  staff-only, but obeys whatever `AdminSite.has_permission` returns.
- Ships pre-built React assets so consumers do not need Node to install
  the package.

Detailed shape is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 2. The five rules

1. **`ModelAdmin` is the only source of truth.** Never build a parallel
   permission, queryset, form, or field-config system.
2. **Never `Model.objects.all()` in API code.** Start from
   `ModelAdmin.get_queryset(request)`.
3. **Writes go through `ModelAdmin.get_form()`.** Deletes go through
   `ModelAdmin.delete_model()`.
4. **Staff-only by default, CSRF always on.** No endpoint is exempt
   without explicit, documented justification.
5. **Every folder has a `README.md`.** If you create one, add it in the
   same commit.

---

## 3. Working agreements

- **PR-only flow.** No direct commits to `main` except the bootstrap empty
  commit. Open a branch matching the work type: `feat/...`, `fix/...`,
  `docs/...`, `chore/...`. For tracked work, link the PR to its
  [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
  card and its driving issue.
- **Autonomous PR ops.** Sessions pick a role — Author, Reviewer, Merger,
  Releaser — at session start and obey
  [`docs/agents/pr-workflow.md`](docs/agents/pr-workflow.md). The role
  is declared in the PR description (and any review comments the
  session posts). Auto-merge is gated by
  [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md).
  Author ≠ Reviewer ≠ Merger on the same PR. **Approvals happen as PR
  review comments — never as committed markdown files.**
- **Tier 5 / 6 is always human.** Any change to `SECURITY.md`,
  `LICENSE`, `docs/api-contract.md`, `pyproject.toml` deps, frontend
  root `package.json` deps, `.github/workflows/`, CSRF/auth code, or
  the serializer denylist is human-review-only. Releases (PyPI) are
  human + token.
- **One PR per branch.** Keep PRs small; split aggressively.
- **Use Poetry for Python, pnpm for JavaScript.** No mixing.
- **Update docs in the same PR** as the change. Architecture/plan/scope
  changes that don't update the corresponding doc will be reverted.
- **No secrets in commits.** Period. See
  [`SECURITY.md`](SECURITY.md) §5.
- **Tests before or alongside features.** See §6 below for the minimum
  matrix.
- **Boring beats clever.** Stable, readable code beats a clever
  abstraction.
- **Ambiguous → document the assumption.** Append to
  `docs/agents/open-questions.md` and pick the simpler interpretation.
  Do not invent complex designs to hedge.

---

## 4. Multi-agent coordination

Several agents may be running at once. Coordination lives on GitHub —
not in committed markdown — so the surface stays searchable, indexed,
and notification-driven.

1. **Claim a Project board card before opening a PR.** Look at the
   [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
   and the open [Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues).
   Assign yourself (or post a claim comment on the issue) before you
   start. If the issue doesn't exist yet, open one first.
2. **Use GitHub for everything else:**
   - **[Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues)**
     — work tracking. One issue per actionable piece of work.
   - **[Discussions](https://github.com/MartinCastroAlvarez/django-admin-react/discussions)**
     — announcements, Q&A, ideas, show-and-tell. Anything broadcast
     or community-shaped.
   - **PR review comments** — *all* review feedback and *all*
     approvals. Per-PR conversations belong on the PR itself, not in
     committed markdown files.
   - [`docs/agents/decisions.md`](docs/agents/decisions.md) —
     append-only ADRs (one to two lines each, link out for detail).
   - [`docs/agents/open-questions.md`](docs/agents/open-questions.md)
     — questions awaiting a decision that aren't yet shaped for an
     issue or Discussion.
3. **Do not duplicate work.** Before starting, scan the open PR list
   and the assigned cards on the board. If someone is already on it,
   comment on their PR or their card instead of forking the effort.
4. **Public repo, public eyes.** Everything in this repository
   (`docs/`, commits, PR descriptions, commit messages, Issues,
   Discussions) is published. Do not paste secrets, tokens,
   transcripts, private user data, or anything that wouldn't survive
   a public audit.

---

## 5. Folder rule

Every folder has a `README.md` covering:

- What lives here.
- What does **not** belong here.
- Pointers to the most relevant other files.

Adding a folder without a `README.md` is a review-blocking comment. If you
notice an existing folder missing one, fixing it is a low-risk win.

---

## 6. Test minimums

For every API endpoint added:

- Anonymous user → not authorized (login redirect or `403`, no body
  leakage).
- Authenticated non-staff user → `403`.
- Staff user with permission → success.
- Staff user without the relevant `has_*_permission` → `403`.
- Unregistered model → `404`.
- Non-existent `pk` → `404`.
- Write attempts to `exclude`/`readonly_fields` → `400`, value
  unchanged.
- CSRF missing on unsafe method → `403`.
- Returned `permissions` booleans match `ModelAdmin.has_*_permission`.

Plus whichever feature-specific cases your endpoint introduces.

---

## 7. Frontend rules

- React packages live under `frontend/packages/` as a pnpm workspace.
- No frontend code may know about example models (`Account`, `Book`,
  `Transaction`, ...). The UI is metadata-driven; if the API doesn't
  provide the metadata you need, fix the API, not the UI.
- Components live in `@dar/ui` only if they have generic, reusable props
  and no business knowledge. Anything model-aware lives in `@dar/list`,
  `@dar/details`, or `@dar/models`. App-shell chrome is isolated too:
  `@dar/sidebar` (navigation chrome) and `@dar/settings` (the Settings
  dialog + theme), so `@dar/web` stays a thin composition layer.
- **Data flow is one-way and gated by `@dar/data`.**
  - `@dar/api` is the only package that talks to the backend (React
    Query + fetch).
  - `@dar/data` is the only package that imports `@dar/api`. It owns
    the localStorage cache, the React Context providers, and the
    debounce buffer for user-initiated mutations.
  - `@dar/list`, `@dar/details`, `@dar/models`, `@dar/search`,
    `@dar/sidebar`, `@dar/settings`, and `@dar/web` import **only**
    `@dar/data` (and `@dar/ui` / sibling UI packages). Importing
    `@dar/api` from a UI package is a CI-failing lint rule.
- Tailwind for styling. Theme overrides go through CSS variables or the
  exported Tailwind config; runtime config swapping is out of scope for
  v1.
- **No redundant chrome — let self-evident UI speak for itself.** When a
  control or form already explains itself through its labels and
  affordances, do **not** add explanatory text or extra buttons:
  - No modal subtitle restating what the form obviously does (a list of
    show/hide checkboxes does not need "Show or hide list columns").
  - No "Done" / "Close" footer button whose only job is to close — the
    `Modal` already closes on the `✕`, `Esc`, backdrop click, and mobile
    back. Footers are for **actions** (Delete, Run, Clear all, Save).
  - No "always shown" / "disabled" caption next to an already-disabled
    control — the disabled state is the signal.
  Only add text when it conveys something **non-obvious** (e.g. "Saved on
  this device" = the pref is device-scoped, not synced; "clears cached
  data" = a security side effect). When in doubt, cut it.

---

## 8. Git / GitHub etiquette

- Never force-push `main`.
- Never `git config --global` anything.
- Never bypass hooks (`--no-verify`) unless you can explain in the PR why.
- Use `gh pr create` with a HEREDOC body so newlines render correctly.
- Commit messages: imperative mood, ≤72 char subject, body explains why.
- Co-author trailer is fine; never paste tokens in trailers or messages.

---

## 9. When something is wrong

- The kickoff brief and this file disagree → trust this file but flag the
  conflict in `docs/agents/open-questions.md`.
- This file and `ARCHITECTURE.md` disagree → fix this file (it's the
  agent-facing contract) **and** the architecture file in the same PR.
- The code disagrees with both → fix the code, write the test, and
  describe the fix in the PR body. The PR list is the change log.

---

## 10. Last resort

If you are stuck, do **not**:

- Silently change scope.
- Disable a security check to make a test pass.
- Force-push or rewrite shared history to "clean things up".
- Add a feature flag to hide an unfinished feature.

Instead:

- Open a draft PR with what you have. Describe what's stuck in the PR
  body.
- Open a [Discussion](https://github.com/MartinCastroAlvarez/django-admin-react/discussions)
  (Q&A category) if the blocker is a *question* that needs an answer
  from a human or another agent.
- Append the question to `docs/agents/open-questions.md` if it's
  shaped like an architectural decision waiting for input.

The next agent (or the human reviewer) will pick it up.
