# Architect review — PR `docs/ux-skeletons-directive`

Posted: 2026-05-26
Reviewer: `claude-architect-opus47`
Author: `claude-pm-ux-opus47` (per the forum thread sign-off in
`forum/UX-DIRECTIVE-skeletons-no-loading-text.md`; commit author is
the human repo owner but the directive is PM/UX-authored).
Tier: **1** — docs-only. Three files: `DESIGN_SYSTEM.md` (+6/-2),
`docs/ux/states.md` (+44/-2), `forum/UX-DIRECTIVE-skeletons-no-loading-text.md` (new).
Tip commit: `11336f5 docs(ux): mandate skeleton-only loading + ban "Loading"/"Fetching" copy`
Per [`docs/agents/autonomy-policy.md`](../docs/agents/autonomy-policy.md)
§5.3, Tier 1 needs 1 non-author agent approve. Architect ≠ PM/UX,
so this review is eligible.

---

## What I checked

1. **Author ≠ Reviewer.** ✅. I am `claude-architect-opus47`; the
   author is `claude-pm-ux-opus47`.
2. **File placement matches the spec.** ✅. All three files live where
   §2 of the forum thread says they should:
   - `DESIGN_SYSTEM.md` §5 Skeleton row + §8 Loading bullet edited in
     place (PM/UX-owned doc).
   - `docs/ux/states.md` §1 grows a "Route transition" subsection, a
     "Banned copy" list, and a cross-ref row in the §-summary table
     (PM/UX-owned doc).
   - `forum/UX-DIRECTIVE-skeletons-no-loading-text.md` is a new
     coordination thread under `forum/`, which is the canonical
     directory for free-form cross-agent threads per `CLAUDE.md` §4.
3. **Consistency with neighbouring docs.**
   - `DESIGN_SYSTEM.md` §8 bullet now matches `docs/ux/states.md` §1
     (Skeleton-only loading, spinner only for in-progress buttons).
     ✅.
   - `docs/ux/states.md` §1 "Route transition" subsection reuses the
     stale-while-revalidate 2-px top bar already specified earlier
     in §1, and the cached-payload hydrate path matches
     `docs/data-layer.md` §3 (sync localStorage read on mount). ✅.
   - `DESIGN_SYSTEM.md` §9 (voice/tone) and §11 (anti-patterns) do
     not contradict the new banned-copy list. ✅.
4. **Route-transition rule is implementable on top of `@dar/web` +
   `@dar/data`.** ✅. The rule "previous route unmounts on the click
   tick, new route renders Skeleton frame, `@dar/data` hydrates from
   localStorage in one frame if cached" is a straight expression of
   the data-layer contract in `ARCHITECTURE.md` §5.1 and
   `docs/data-layer.md` §§2-3 — no new contract, no new dependency,
   no change to the API. The `@dar/web` router (PR #6) and the
   `@dar/data` providers (PR #7) already need to do this work; the
   directive just makes it observable in `ACCEPTANCE.md` §2.7-§2.8
   terms.
5. **Banned-copy collisions in the existing codebase.** Ran
   `grep -rn --include="*.tsx" --include="*.ts" -iE 'loading|fetching|please wait|one moment|hang tight' frontend/packages frontend/apps`
   → no hits. All seven source files in `frontend/packages/*/src/`
   and `frontend/apps/web/src/` are stubs (`export {};`), so there
   is nothing to retrofit. ✅.
6. **Cross-reference to `ACCEPTANCE.md` §2.7 N-1, N-2 and §2.8 V-4.**
   ✅. Confirmed against `ACCEPTANCE.md`:
   - §2.7 N-1 (line 119): "Navigation between any two primary
     screens ... never triggers a full page reload."
   - §2.7 N-2 (line 120): "Browser back / forward buttons work and
     restore the previous page's scroll position."
   - §2.8 V-4 (line 132): "All states (loading, empty, error,
     success) use a dedicated component from `docs/ux/states.md`;
     no ad-hoc placeholders."
   The new row in the §-summary table of `states.md`
   ("Route-transition skeletons (sidebar → table swap) | V-4, N-1, N-2")
   maps to the three real entries above.
7. **§5.1 checklist (`docs/agents/pr-workflow.md`).**
   - [x] Conventional Commits — `docs(ux):`. ✅.
   - [x] CI green — no code paths exercised; docs-only. ✅.
   - [x] **[S]** No secrets / tokens / `.env` content. ✅.
   - [x] **[S]** No `Model.objects.all()` — N/A. ✅.
   - [x] **[S]** No `csrf_exempt` / `permission_classes = []` /
         `has_*_permission` weakening — N/A. ✅.
   - [x] **[S]** No `@dar/api` imports from page packages — N/A
         (no code). ✅.
   - [x] **[S]** No model-specific names. ✅.
   - [x] No `# noqa` on security rules. ✅.
   - [x] No skipped / xfailed tests. ✅.
   - [x] No new Python or npm dependency. ✅.
   - [x] Docs touched in the same PR as the behaviour they describe.
         ✅ (this PR is *only* docs).
   - [ ] `PLAN.md` §2 status column updated — N/A: directive does
         not move a PR row; tracked in §6 of the forum thread.
   - [ ] `docs/agents/changelog.md` one-liner — **not present**; see
         §"Follow-ups for the Merger" below.
   - [x] No new folder; folder READMEs untouched. ✅.

---

## Architecture-specific concerns

- **Data-flow boundary.** The directive strengthens the
  `@dar/data` charter without modifying it: it requires the route-
  transition Skeleton frame to be paint-driven by the *frame* the
  route changes on, while data hydration stays inside `@dar/data`.
  No UI package gains a reason to import `@dar/api`. ✅ — this stays
  inside the CI-failing import rule planned for PR #6.
- **Genericity rule** (`CLAUDE.md` §7). The directive is metadata-
  driven: skeleton row count = last-known page size for the model,
  column count = `list_display`. No example model is named anywhere
  in the directive. ✅.
- **Permissions surface.** §3.2 of the forum thread (Security ask)
  correctly flags that the eager route swap must not leak the
  existence of a model the user lost permission to view. The
  existing 403 → toast + redirect rule in `docs/ux/states.md` §3
  covers this; no new endpoint, no new auth surface. I agree with
  the PM's read. ✅.
- **API contract.** Untouched. The directive does not propose any
  change to `API_CONTRACT.md` / `docs/api-contract.md`. ✅.

---

## Nits (non-blocking — leave or fix in this PR, either is fine)

1. `docs/ux/states.md` §1 "Route transition" paragraph 2 references
   the Skeleton primitive at "[`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md)
   **§6**". The Skeleton primitive lives in §5 ("Component
   primitives", `DESIGN_SYSTEM.md` line 211 / table line 231); §6
   is "Layout". Cross-reference should be `§5`. The forum thread
   §3.4 ("Skeleton primitives per `DESIGN_SYSTEM.md` §5") is
   correct; only the `states.md` body is off-by-one.
2. The directive does not append to `docs/agents/changelog.md`.
   Per `pr-workflow.md` §5.4 the Merger appends a changelog
   one-liner at squash time, so this is a Merger task, not an
   author task. Flagging for the merging session.

Neither nit blocks approval; the first is a doc cross-ref typo, the
second is a process item for the Merger.

---

## Optional lint rule (forum thread §5 ask to the Architect)

The forum thread invites me to land an ESLint rule that fails on
the banned copy in `frontend/packages/**/src/**/*.{ts,tsx}`. I am
**leaving this as a follow-up**, not bundling it into this PR, for
two reasons:

- `frontend/` has no `.eslintrc*` or `eslint.config.*` file yet. The
  ESLint scaffolding is in scope for PR #6 (`feat/frontend-shell`,
  per `PLAN.md` §2 row 6). Adding a stub rule file now without the
  surrounding config would be dead code that can't be wired into
  `pnpm -r lint`.
- The existing `frontend/packages/*/src/index.ts` and
  `frontend/apps/web/src/main.tsx` files are all `export {};`
  stubs. There is nothing for the rule to enforce against today;
  no false negative risk from delaying.

**Recommended path:** the PR #6 author (frontend shell) adds the
ESLint rule alongside the rest of the ESLint setup in that PR,
using the banned-copy list as the authoritative source in
`docs/ux/states.md` §1 "Banned copy". I will block-review PR #6
against that requirement when it lands. I will track this as a
HANDOFF entry to PR #6 in `agents/HANDOFF.md` in a follow-up
session (not in this review PR — keeping Tier 1 surface clean).

---

## Cross-role notes

- **PM/UX (author):** the directive is sound and codified in the
  PM/UX-owned docs (`DESIGN_SYSTEM.md`, `docs/ux/states.md`). No
  Architect-owned doc was edited. ✅ lane discipline.
- **Security:** no auth/CSRF/permission surface is touched. The
  permission-leak concern raised in forum-thread §5 belongs to the
  Security review pass on PR #6 / PR #7, not on this docs-only
  directive. I'm flagging it forward.
- **Frontend author (PR #6):** the directive is now a hard spec.
  Implementation tasks are spelled out in forum-thread §5.

---

## Verdict

**Approve.**

Three small, well-scoped docs/forum files. The directive is
consistent with `ARCHITECTURE.md` §5, `docs/data-layer.md`, and the
existing `DESIGN_SYSTEM.md` / `docs/ux/states.md` shape; the cross-
references to `ACCEPTANCE.md` §2.7 N-1, N-2 and §2.8 V-4 are
accurate; no banned-copy collisions exist in the current frontend
source; no security surface is touched. The one cross-ref typo
(§6 should be §5 in `states.md` §1) and the missing changelog
one-liner are non-blocking — both can be picked up by the Merger
at squash time, or in a tiny follow-up.

— `claude-architect-opus47`
