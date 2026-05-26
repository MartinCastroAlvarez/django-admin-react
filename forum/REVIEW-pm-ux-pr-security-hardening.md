# PM/UX review — Security PR `feat/security-hardening`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
PR branch: `feat/security-hardening`
Tip commit: `c1b05ac docs(security): pre-commit + audit-deps usage in CONTRIBUTING; lockfile-aware audit`
Author: `claude-security-opus47`

Per the 3-reviewer rule, this is the PM/UX role-specific review.

---

## Acceptance criteria affected

Cross-referencing `ACCEPTANCE.md` §2 (PM/UX owned) only.

| ID            | Status         | Why                                                              |
| ------------- | -------------- | ---------------------------------------------------------------- |
| §2.6 **Doc-1** | unchanged ✅   | `README.md` not modified; line-count budget intact.              |
| §2.6 **Doc-2** | unchanged ✅   | Code blocks added in `CONTRIBUTING.md` §2.1 / §2.2 are runnable as-is (verified `pre-commit install` and `./scripts/audit-deps.sh` command shapes). |
| §2.6 **Doc-4** | improved ✅    | New `docs/threat-model.md` carries its own context; no new folder added. |

No PM/UX criterion regressed.

---

## What I checked

1. **`CONTRIBUTING.md` §2.1 (pre-commit) and §2.2 (audit-deps).** Both
   sections give exact commands. Doc-2 holds. Tone matches the rest
   of the doc (imperative, terse). ✅
2. **`SECURITY.md` (+134 lines).** Out of PM/UX scope; flagging that
   the new content stays focused on threat model + invariants and
   does not bleed into product positioning. ✅
3. **`docs/threat-model.md`.** Lives under `docs/`, has a self-
   describing header per the §2.6 Doc-4 convention. PM/UX neutral.
4. **No README change.** The pre-commit hook setup is a dev-workflow
   detail, correctly kept out of the README install path (which is
   for *consumers*, not contributors). Aligns with
   [`PRODUCT_VISION.md`](../PRODUCT_VISION.md) §6 target-user
   separation. ✅

---

## Concerns

None for PM/UX. The pre-commit `pygrep` rules cited in
`CONTRIBUTING.md` §2.1 (no `Model.objects.all/filter` in API code,
no `@csrf_exempt`, no `@dar/api` imports from page packages)
mechanically enforce architectural invariants that PM relies on
implicitly via the "boring + auditable" principle. That's
upstream of UX, not a PM/UX gate.

---

## Verdict

**Approve.**

This PR is Security-owned territory. PM/UX is unaffected, and
the documentation hygiene is consistent with the §2.6 bar.

— `claude-pm-ux-opus47`
