# PM/UX review — PR `chore/api-rename-destroy-drop-app-name`

Posted: 2026-05-26
Reviewer: `claude-pm-ux-opus47` (Product / UX)
Tip commit: `7663d1a refactor(api): rename views/delete.py → views/destroy.py; drop unused api_v1 URL namespace`
Tier: **3** (internal backend refactor; no security surface change).

---

## Acceptance criteria affected

| ID                | Status | Why                                                                                          |
| ----------------- | ------ | -------------------------------------------------------------------------------------------- |
| §2.2 **D-4**      | ✅ (unchanged) | Internal rename only; consumer-visible Python surface unaffected.                       |
| §2.6 **Doc-3**    | ✅ (unchanged) | Wire contract in `docs/api-contract.md` is unchanged — the SPA's URL building works through the contract, not Django `reverse()`. |
| §2.6 **Doc-4**    | ✅ (unchanged) | No new folder.                                                                                |
| §2.9 **E-1**      | ✅ (unchanged) | `ModelAdmin` is still the only extension surface; nothing about `ModelAdmin.delete_model` is renamed.                                                  |

No PM/UX criterion regressed. No README, ONBOARDING, or docs/ux/ touch
required.

---

## What I checked

1. **External wire contract unchanged.** `docs/api-contract.md` §5.3
   still describes `DELETE /api/v1/<app>/<model>/<pk>/`; the HTTP
   verb is preserved (Django CBV's `delete()` handler is the name
   required by the framework). ✅
2. **Naming consistency with the rest of the API.** Files in
   `django_admin_react/api/views/` are now: `create.py`, `update.py`,
   `destroy.py`, `list.py`, `detail.py`, `registry.py`. DRF-style and
   consistent. ✅
3. **No reverse() usage in the SPA path.** The SPA builds URLs from
   the contract; dropping the `api_v1` namespace is safe. The
   `django_admin_react:<name>` outer namespace stays for any
   consumer needing `reverse()`. ✅
4. **Test fix on `test_s26_no_csrf_exempt_in_package`.** This is a
   net security improvement — the prior regex matched docstring
   mentions of `@csrf_exempt` (which exist to *document the
   absence* of it). The tightened regex only matches the actual
   decorator. Doesn't weaken the security invariant. ✅
5. **Test count.** Commit body claims `137 passed, 1 xfailed` after
   the rename. No skipped/xfailed tests added by this PR. ✅

---

## Concerns

None for product/UX. The rename is small, isolated, and follows
DRF convention without leaking an external naming decision into
the consumer's mental model of Django admin.

---

## Verdict

**Approve.**

Internal refactor, zero §2 / §3 / §4 acceptance impact. Net positive
on test-regex precision.

— `claude-pm-ux-opus47`
