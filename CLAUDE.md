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

Read these files, in order, every session:

1. [`CLAUDE.md`](CLAUDE.md) — this file. Check for updates since last
   session.
2. [`PLAN.md`](PLAN.md) — current PR sequence, scope, assumptions.
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — the architectural contract.
4. [`SECURITY.md`](SECURITY.md) — non-negotiable security rules.
5. [`docs/agents/decisions.md`](docs/agents/decisions.md) — accepted
   decisions.
6. [`docs/agents/open-questions.md`](docs/agents/open-questions.md) —
   open questions; do not re-decide things already answered in
   `decisions.md`.
7. [`docs/agents/changelog.md`](docs/agents/changelog.md) — what other
   agents have shipped recently.
8. [`docs/agents/pr-workflow.md`](docs/agents/pr-workflow.md) — the
   author/reviewer/merger protocol for autonomous PR ops. **Pick your
   role for the session before any tool call.**
9. [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md)
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
  commit. Open a branch `pr/<NN>-<slug>` for planned PRs (see
  [`PLAN.md`](PLAN.md)), or `feat/...` / `fix/...` / `docs/...` /
  `chore/...` otherwise.
- **Autonomous PR ops.** Sessions pick a role — Author, Reviewer, Merger,
  Releaser — at session start, post the role to `forum/`, and obey
  [`docs/agents/pr-workflow.md`](docs/agents/pr-workflow.md). Auto-merge
  is gated by [`docs/agents/autonomy-policy.md`](docs/agents/autonomy-policy.md).
  Author ≠ Reviewer ≠ Merger on the same PR.
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

Several agents may be running at once. To avoid collisions:

1. **Pick an in-flight or unclaimed PR slot.** Look at branches on the
   remote (`git ls-remote --heads origin`) and at
   [`PLAN.md`](PLAN.md) §2. If the next planned PR is unclaimed, claim it
   by opening a draft PR with `[WIP]` in the title and a checklist.
2. **Coordinate in `docs/agents/` and `forum/`.**
   - [`docs/agents/decisions.md`](docs/agents/decisions.md) — accepted
     decisions (append-only).
   - [`docs/agents/open-questions.md`](docs/agents/open-questions.md) —
     questions awaiting a decision.
   - [`docs/agents/changelog.md`](docs/agents/changelog.md) — one line
     per merged PR.
   - [`forum/`](forum/) — free-form threads, one `.md` per topic. Sign
     your messages (e.g., `— claude-foundation`).
3. **Do not duplicate work.** If another agent is already on the branch
   you wanted, leave a comment on their PR and pick the next item.
4. **Public folder, public eyes.** Everything in `docs/agents/` and
   `forum/` is committed to a public open-source repository. Do not paste
   secrets, tokens, transcripts, private user data, or anything that
   wouldn't survive a public audit.

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
  `@dar/details`, or `@dar/models`.
- **Data flow is one-way and gated by `@dar/data`.**
  - `@dar/api` is the only package that talks to the backend (React
    Query + fetch).
  - `@dar/data` is the only package that imports `@dar/api`. It owns
    the localStorage cache, the React Context providers, and the
    debounce buffer for user-initiated mutations.
  - `@dar/list`, `@dar/details`, `@dar/models`, and `@dar/web` import
    **only** `@dar/data` (and `@dar/ui`). Importing `@dar/api` from a
    UI package is a CI-failing lint rule.
- Tailwind for styling. Theme overrides go through CSS variables or the
  exported Tailwind config; runtime config swapping is out of scope for
  v1.

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
- The code disagrees with both → fix the code, write the test, and add a
  `docs/agents/changelog.md` line.

---

## 10. Last resort

If you are stuck, do **not**:

- Silently change scope.
- Disable a security check to make a test pass.
- Force-push or rewrite shared history to "clean things up".
- Add a feature flag to hide an unfinished feature.

Instead:

- Open a draft PR with what you have.
- Write a note in `forum/` describing where you got stuck.
- Append the question to `docs/agents/open-questions.md`.

The next agent (or the human reviewer) will pick it up.
