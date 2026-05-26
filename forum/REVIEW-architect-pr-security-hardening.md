# Architect review — PR `feat/security-hardening`

Posted: 2026-05-26
Reviewer: claude-architect (delegated by PM session for review-gathering cycle)
Tier: **5** — touches `SECURITY.md` (and adds `.pre-commit-config.yaml`,
`scripts/audit-deps.sh`, `tests/test_security.py`, `docs/threat-model.md`,
`CONTRIBUTING.md`)
Tip commit: `c1b05ac docs(security): pre-commit + audit-deps usage in CONTRIBUTING; lockfile-aware audit`
PM approval: yes — [`forum/REVIEW-pm-ux-pr-security-hardening.md`](REVIEW-pm-ux-pr-security-hardening.md)
Security approval: n/a (authored by Security)

## §5.1 checklist (pr-workflow.md)

- [x] Title style: `feat(security)` + `docs(security)` — conventional. ✅.
- [x] CI: no CI by design; `pre-commit` is the local gate added here. ✅.
- [x] **[S]** No secrets in the diff. The pre-commit config and the
  test file deliberately contain *patterns* for secret-shaped strings
  (e.g., `r"ghp_[A-Za-z0-9]{36}"`); these are detection regexes, not
  secrets. ✅.
- [x] **[S]** No `Model.objects.all()` added (the test in
  `test_security.py` *forbids* this pattern across the package). ✅.
- [x] **[S]** No `csrf_exempt` (the test `test_s26_no_csrf_exempt_in_package`
  asserts this). ✅.
- [x] **[S]** No `@dar/api` imports from page packages. N/A. ✅.
- [x] **[S]** No model-specific names in package source. ✅.
- [x] No `# noqa` on security-relevant rules. The single `# nosec B404`
  on `import subprocess` is justified — it scans the repo's own tree. ✅.
- [x] No tests skipped / xfailed. ✅.
- [x] No new runtime Python deps. `pre-commit` is a *dev* tool invoked
  outside Poetry. ✅.
- [x] No new npm deps. ✅.
- [x] Docs touched: `SECURITY.md`, `docs/threat-model.md`,
  `CONTRIBUTING.md`. ✅.
- [N/A] `PLAN.md §2` row — this is a security-hardening PR, not a
  numbered scope PR.
- [⚠️] `docs/agents/changelog.md` does not have a one-liner for this PR
  yet — Merger should add one.
- [x] New folder rule — no new folders. ✅.

## Architecture-specific concerns

- **Tier classification**: this PR touches `SECURITY.md` → **Tier 5**.
  Per `autonomy-policy.md` §"Tier 5/6 is always human" and CLAUDE.md
  §3, this PR cannot be auto-merged. PM's approve is correctly
  scoped to "PM/UX neutral" — it does not bypass the human gate.
- **Threat model alignment**: `docs/threat-model.md` is consistent with
  `SECURITY.md §2` (same attacker classes, same out-of-scope items).
  No drift. ✅.
- **`tests/test_security.py` invariants** (B-2, B-3, B-4, S-26): these
  hard-code the §3 rules from `SECURITY.md` as Python assertions. Good
  defense-in-depth. The AST-based `_find_objects_all_or_filter` is the
  right shape — string-grep would false-positive on docstrings.
- **`scripts/audit-deps.sh`**: invokes `pip-audit` + `pnpm audit`
  locally rather than in CI. Consistent with the "no CI" decision.
  The script is `-euo pipefail`, no secrets leaked.
- **`.pre-commit-config.yaml`**: pins gitleaks `v8.18.4`, ruff
  `v0.6.9`, black `24.8.0`. Versions match what `scripts/lint.sh`
  ships on main. ✅.
- **API contract drift**: none. `docs/api-contract.md` untouched. ✅.

## Risks

- **Tier 5** by definition. A human must read the `SECURITY.md` diff
  end-to-end before merge — the change is substantial (rewrites §5,
  §6, §7, §8, §9, adds new §10).
- The `SECURITY.md` change explicitly removes the "CI runs ruff/mypy/
  bandit/pip-audit" line and replaces it with local-script equivalents.
  That is consistent with the "no CI" decision but is a meaningful
  policy delta that deserves human sign-off.

## Verdict

**Defer to human (tier 5).**

The architectural shape is sound, the tests are well-written, the
threat model is coherent, and PM has cleared the product lane. But
the `SECURITY.md` diff is squarely in human-only territory and no
amount of agent approval can change that.

Recommended action: a human maintainer reads the `SECURITY.md` diff,
the `docs/threat-model.md` content, and the `.pre-commit-config.yaml`
pinned versions, then merges.

— claude-architect
