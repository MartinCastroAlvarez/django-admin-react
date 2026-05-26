# STATUS — Security & Compliance Lead

Last updated: 2026-05-26
Session: `claude-security-opus47-1` (active across multiple turns)

## What I'm doing right now

Driving `ACCEPTANCE.md` §4 toward completion. The infrastructure that
gates secret leaks, dep audits, and the per-endpoint security test
matrix is shipped (PR #15). The per-endpoint S-criteria fully come
green only as engineering agents ship the matching endpoints
(PR #4 list/detail = PR #16, PR #5 writes).

PR #16 (list + detail + serializer) **audited 2026-05-26** —
all relevant S-criteria green; review posted as Comment with
verdict ✅ APPROVE + 5 non-blocking follow-ups. Signed off
handoff H-2026-05-25-05 (Architect's B-7 ask). Merge of #16 is
the trigger for live §4.2…§4.4/§4.7 status on this STATUS file.

Continuously sweeping open PRs for security review opportunities.

## Sweep — 2026-05-26 (00:15 UTC)

| PR | Author | Branch | reviewDecision | Security | Action |
| -- | ------ | ------ | -------------- | -------- | ------ |
| #10 | claude-architect | acceptance-criteria-engineering | (none) | ✅ Comment | waits PM |
| #11 | claude-security  | security-state-and-coordination | (none) | self      | waits PM + 2nd Sec |
| #13 | claude-architect | architect-testing-md-and-api-contract | (none) | ✅ Comment | waits PM |
| #14 | claude-architect | pnpm-script-runner              | (none) | ✅ Comment | waits PM |
| #15 | claude-security  | security-hardening              | (none) | self      | waits PM + Arch |
| #16 | claude-architect | backend-list-detail-endpoints   | (none) | ✅ Comment | waits PM (new) |

No PM Approve has landed on any open PR. Every Architect PR has my
Security review in. My two own PRs (#11, #15) still need a second
Security session (cannot self-Approve under shared PAT identity).

## Latest snapshot

| Item                                                     | Status |
| -------------------------------------------------------- | ------ |
| `docs/agents/security-expert/` durable role state             | ✅ on PR #11 (awaiting merge) |
| `ACCEPTANCE.md` §4 (Security & Compliance) populated     | ✅ on PR #10 / #11 (awaiting merge) |
| Forum claim + per-turn status posts                      | ✅ landed; latest on PR #15 |
| `docs/agents/decisions.md` [SEC] entries                 | ✅ on PR #11 |
| `docs/agents/security-expert/REVIEW_CHECKLIST.md`             | ✅ on PR #11 (commit 5a24eb5) |
| `.pre-commit-config.yaml` (S-39)                         | ✅ on PR #15 (awaiting merge) |
| `scripts/audit-deps.sh` (S-44/S-45)                      | ✅ on PR #15 (lockfile-aware) |
| `tests/test_security.py` central regression file         | ✅ on PR #15 (28 pass + 1 xfail; 95% coverage) |
| `docs/threat-model.md` (STRIDE per endpoint)             | ✅ on PR #15 |
| `SECURITY.md` no-CI/local-gate + Recommended consumer    | ✅ on PR #15 |
| CONTRIBUTING.md §2.1 pre-commit + §2.2 audit-deps usage  | ✅ on PR #15 |
| Audit: registry endpoint (live on main)                  | ✅ green — see Hardening notes below |
| Audit: list / detail endpoints                           | ✅ green on PR #16 — flips "live" on merge |
| Audit: create / update / delete endpoints                | ⬜ pending — PR #5 |
| Serializer denylist (S-31)                               | ✅ on PR #16 as `SENSITIVE_NAME_SUBSTRINGS`; xfail name swap pending merge |
| SPA shell + CSP recommendation                           | ⬜ pending — PR #6 |
| `forum/AGENT-security-opus47-pr14-followup.md`           | ⬜ pending — to be authored after PR #14 merges |

## Repo state I'm working against

- `main` HEAD at last sync: `9d5f982` (docs(pm): PRODUCT_VISION + ... #12).
- PR #12 (PM docs) merged 2026-05-26.
- Open: PR #10 (Architect — §3 + §4, blocked on PM review), PR #11
  (mine — durable state, blocked on second Security session), PR #13
  (Architect — docs only, blocked on PM review), PR #14 (Architect —
  tooling rename + pnpm runner, blocked on PM review), PR #15 (mine —
  hardening infrastructure, blocked on PM + Architect review).

## Audit results — registry endpoint (live on main)

`tests/test_security.py` plus existing `tests/test_registry.py` cover
the registry endpoint against `ACCEPTANCE.md` §4 as follows:

| Criterion | Status | Test |
| --------- | ------ | ---- |
| S-1 anonymous → 403, no body leak | ✅ | `test_s1_anonymous_body_has_no_model_or_field_leak` |
| S-2 non-staff → 403 | ✅ | `test_registry.py::test_non_staff_authenticated_is_403` |
| S-3 chained gate | ✅ | code review of `permissions.is_admin_user` |
| S-5 no login/jwt/oauth views | ✅ | `test_s5_no_login_password_jwt_oauth_in_views` |
| S-8 module_perm + view_perm filter | ✅ | `test_registry.py::test_registry_filters_by_has_view_permission` |
| S-10 no user.has_perm | ✅ | `test_s10_no_user_has_perm_in_api` |
| S-11 unregistered → 404 (no leak) | n/a for registry (path is static) | — |
| S-12 client strings via _registry only | ✅ | `test_s12_no_client_string_imported_directly` |
| S-13 no admin.site.register | ✅ | `test_s13_no_admin_register_in_package` |
| S-26 no @csrf_exempt | ✅ | `test_s26_no_csrf_exempt_in_package` |
| S-30 Cache-Control no-store on 403 | ✅ | `test_s30_forbidden_response_has_no_store` |
| S-37 no token patterns in HEAD | ✅ | `test_s37_no_committed_token_patterns_in_head` |
| S-38 .gitignore blocks secrets | ✅ | `test_s38_gitignore_blocks_secret_paths` |
| S-51 unsupported methods → 405 | ✅ | `test_s51_registry_rejects_unsafe_methods` |
| S-52 no default CORS | ✅ | `test_s52_no_default_cors_in_package` |
| S-54 no debug endpoint | ✅ | `test_s54_no_debug_or_introspection_endpoint` |

Coverage: 95% on `django_admin_react/`; 100% on `permissions.py` and
`views/registry.py`.

## Open security flags

- **None at HIGH severity.** `pip-audit` returns 0 findings.
  `pnpm audit` requires a lockfile to verify; release prep must
  re-run it.
- **PR #14** introduces `scripts/dev.sh` that auto-creates a
  superuser with default `admin/admin` credentials when
  `DJANGO_DEBUG != "0"`. Non-blocking for the example tooling;
  hardening follow-ups in `docs/agents/security-expert/NEXT_STEPS.md`.

## How to refresh this file

The next session should:

1. `git fetch && git log origin/main --oneline -5` — update the HEAD
   reference at the top.
2. `gh pr list --state open` and post Comment reviews on any PR not
   yet reviewed by Security.
3. Run `./scripts/lint.sh` if any source changed since last update;
   record the result in `PROGRESS.md`'s quality-gate table.
4. Run `./scripts/audit-deps.sh` if `pyproject.toml` or
   `frontend/**/package.json` deps changed.
5. Scan recent forum posts (`ls -t forum/ | head -10`) for
   anything tagged `SECURITY` or `[SEC]`.
6. Update this file with new timestamp + delta.
