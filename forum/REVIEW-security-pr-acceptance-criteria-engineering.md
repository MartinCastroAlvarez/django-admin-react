# Security review — PR `feat/acceptance-criteria-engineering`

Posted: 2026-05-26
Reviewer: `claude-security-opus47` (delegated by PM session for review-gathering cycle)
Tier: 1 (docs only — `ACCEPTANCE.md`, `agents/**`, `docs/agents/decisions.md`)
Tip commit: `7bf01c4 docs(architect): internalize multi-agent review workflow`
Author: `claude-architect`

## §5.1 [S]-checklist (pr-workflow.md)

- [x] No secrets / tokens / keys / PEMs / `.env` content. Two
      meta-mentions of the `ghp_/gho_/ghs_` token prefixes appear in
      `ACCEPTANCE.md` §4.8 S-37 and S-39 as the **rule text itself**
      (defining what is forbidden). One literal `ghp_…XYZ` partial
      redaction pattern is quoted as an example of what S-37 forbids;
      it is not a real secret. ✅ (with NOTE — see "Threats" §1).
- [x] No `Model.objects.all/filter/get/exclude` added in `django_admin_react/`. ✅ (no code in this PR)
- [x] No `csrf_exempt`, `permission_classes = []`, `has_*_permission`
      weakening. ✅ (no code; the doc *requires* CSRF stays on)
- [x] No frontend imports of `@dar/api` from page packages. ✅ (no frontend)
- [x] No model-specific names in `django_admin_react/` or
      `frontend/packages/`. ✅
- [x] No `# noqa` on a security-relevant rule. ✅ (no code)
- [x] No tests skipped/xfailed. ✅ (no tests)
- [x] No new third-party Python dep without `docs/agents/decisions.md`
      entry. ✅ (no `pyproject.toml` touch)
- [x] No new third-party npm dep in generic packages. ✅
- [x] Docs touched if behavior changed. ✅ (this PR *is* docs)
- [x] `PLAN.md` §2 status column. N/A — Architect's `STATUS.md` carries
      the status board for this role.
- [x] New folder `agents/software-architect/` has README content via
      `AGENT.md` (acceptable; matches PM/Security pattern). NOTE — a
      literal `README.md` is also fine; `agents/README.md` already
      documents the convention. ✅

## ACCEPTANCE.md §4 spot-check

§4 is the Security section. This PR *adds* the §4 scaffold (S-1 through
S-66 + B-1 through B-8) authored by the Security role on the
`feat/security-state-and-coordination` branch. The §4 here matches that
branch byte-for-byte (Architect copied the security-authored content
into the Architect PR for §3 to land alongside).

No invariant in §4 is **weakened**. S-31 denylist set, S-26 CSRF rule,
S-15 queryset rule, S-20 form rule, B-7/B-8 release blockers all match
`SECURITY.md` §3 verbatim. ✅

Architect's §3 criteria (B-1 … B-8 engineering blockers) are consistent
with security invariants: B-2 forbids `.objects.all()`, B-3 forces
writes through `get_form()`, B-6 forbids `csrf_exempt`. No tension.

## Threats specific to this PR

1. **`ghp_…XYZ` partial-redaction pattern in S-37 rule text** is
   *describing* the forbidden pattern. Pre-commit `gitleaks` may flag
   it on every subsequent PR. NOTE-level — recommend wrapping in code
   fences and/or replacing with `GH_PREFIX_FOLLOWED_BY_HEX` placeholder
   in a follow-up PR. Not a blocker (the redaction itself is not a
   live secret).
2. No new attack surface. The PR adds **measurable criteria** that
   make the existing security contract auditable; it does not add
   endpoints, dependencies, or settings keys.
3. The Architect's `AGENT.md` "Mandatory invariants" list mirrors
   `SECURITY.md` §3 rules — no drift detected.

## Verdict

**Approve (already merged — close branch).**

This branch was squash-merged into `main` as **PR #11**
(`c074e3c feat: ACCEPTANCE §3 + §4 + agents/{architect,security}
durable state (#11)`). Every file in the diff is byte-identical
between `origin/feat/acceptance-criteria-engineering` and
`origin/main`. The branch is **stale** — the Merger should close the
PR with the "already merged" reason and delete the remote branch.

For the audit record: doc-only Tier 1 PR. The §3 engineering criteria
reinforce, never weaken, the security invariants. The §4 Security
column was authored by Security and matches the source branch.

Follow-up (non-blocking, applies to `main` now): the `ghp_…XYZ`
example in `ACCEPTANCE.md` §4.8 S-37 will trip secret-scanners on
every future diff that touches it. A future PR may rewrite it as
`<gh-prefix>…<hex>` or fence it in a code block to avoid false
positives.

— `claude-security-opus47`
