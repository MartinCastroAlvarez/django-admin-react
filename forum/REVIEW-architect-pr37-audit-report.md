# [Architect] Review — PR #37: full security audit report 2026-05-26

Role: Architect.
PR: #37 — `docs(security): full audit report for 2026-05-26 merge wave`.
Branch: `docs/security-audit-2026-05-26`.
Tier: 1 (`forum/` docs only — single new file, +210 / -0).

## Scope (from an Architect lens)

I checked the audit findings against the actual shape of the code
on post-wave `main`. The question I'm answering: do the
recommendations reflect what an independent architectural pass
would catch, and are the fixes architecturally sound?

## Findings

- **MEDIUM — `Cache-Control: no-store` missing on 200 responses
  is real and correctly framed.** The §4.6 S-30 rule was scoped
  to the 4xx envelopes when it landed, but the 200 path on
  `registry`, list, and detail returns per-user,
  permission-gated data filtered through
  `ModelAdmin.get_queryset(request)` and per-object
  `has_view_permission`. Caching those at an intermediate proxy
  or shared browser cache is a permission bypass, exactly as the
  audit states. The fix in PR #31 — set `no-store` on every 200
  in the three read views — is the minimal correct change and
  matches the architectural invariant (every byte that leaves
  the API is shaped per request.user).
- **LOW — S-31 xfail flip is the right call.** The test was
  scaffolded against a hypothetical `SENSITIVE_FIELD_PATTERNS`
  while PR #17 actually shipped `SENSITIVE_NAME_SUBSTRINGS` at
  `serializers.py:32`. Silently `xfail`-ing means the denylist
  contract was unverified. PR #31's functional companion
  (`test_s31_is_sensitive_field_name_matches_required_patterns`)
  is the right shape — it exercises the helper, not just the
  constant's existence.
- **PR #35 follow-ups match what a code-review pass would
  identify.**
  - `SpaIndexView` is still the foundation-era stub; PR #35
    ships the bundle but does not wire it in or apply
    `@ensure_csrf_cookie`. The recommended follow-up PR is the
    correct decomposition.
  - `useSwrCache` keying by `app/model/pk` only is a real
    cross-user-on-shared-device hazard. Including the
    authenticated user pk in the cache key + clearing on 403 is
    the right architectural fix — it preserves the SWR contract
    while restoring the per-user invariant that the API layer
    already enforces.
  - CSP snippet for `docs/installation.md` is a doc-only
    follow-up that does not change package behavior.
- **What the audit got right architecturally.** `ApiClient` does
  CSRF via cookie (not localStorage), `swr-cache.ts` never
  persists tokens, and the `@dar/api` import boundary is
  enforced by `no-restricted-imports` in
  `frontend/.eslintrc.cjs`. Those three observations match the
  `ARCHITECTURE.md` data-flow contract (`@dar/api` is the only
  package that talks to the backend; `@dar/data` is the only
  importer of `@dar/api`).

## Risks

None at this tier. The audit file is forum-only and append-only;
it does not move any architectural surface. The follow-up items
it surfaces (SpaIndexView wiring, per-user SWR keying, CSP
snippet) are all already accounted for in the deferred-work
table and will land as their own PRs under the normal tier
gates.

## Verdict

**Approve.** The findings are architecturally sound, the fixes
in PR #31 match the minimal-correct-change principle, and the
PR #35 follow-up list is correctly scoped and correctly
deferred.

— `claude-architect`, 2026-05-26
