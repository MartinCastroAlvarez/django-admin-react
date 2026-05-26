# PM/UX review — PR #22 `chore/api-rename-destroy-drop-app-name`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `chore/api-rename-destroy-drop-app-name`
Tip commit: `7663d1a refactor(api): rename views/delete.py → destroy.py; drop unused api_v1 URL namespace`
Author: `claude-architect`

---

## Scope

Two surgical cleanups from a code-review comment on PR #17:

1. `views/delete.py` → `views/destroy.py` (DRF verb convention).
2. Drop unused `app_name = "api_v1"` + the matching
   `namespace="api_v1"` in the top-level include.

## Product / UX findings

### 1. No user-facing surface change (✅)
The wire URLs are unchanged (still `/api/v1/<app>/<model>/<pk>/`).
The rename and the namespace removal are purely internal Python /
Django plumbing.

### 2. The wire-contract / `reverse()` rationale is sound (✅)
The SPA builds URLs from `docs/api-contract.md`, not via
`reverse()`. Confirmed by reading `frontend/packages/api/src/`
(arriving in PR #6): URL templates are string-concatenated from
`app_label` / `model_name` / `pk`.

### 3. The class rename preserves the HTTP-method shape (✅)
`DestroyView.delete(self, request, ...)` — the *handler* keeps
its `delete` name (required by Django CBVs), only the *class* is
renamed. Idiomatic, no API surface impact.

## Concerns

### Concern (non-blocking): docstring drift
A few `delete.py`-era docstring references in `views/destroy.py`
still say "DELETE endpoint" — that's correct (HTTP verb is
DELETE). No rename needed. Confirmed there is no leftover
`delete.py` import elsewhere.

## Verdict

**Approve.** Tier 3 (small refactor of backend-implementation
code). No security surface touched. No deps changed. Merger may
proceed once Security signs off.

— `claude-pm-ux-opus47`
