# NEXT_STEPS — Security & Compliance Lead

A short, ordered to-do for the next session. When you finish an
item, strike it, append a new one, and update `STATUS.md`.

---

## In flight (this PR — `feat/security-acceptance-and-state`)

- [x] `agents/security-expert/AGENT.md`
- [x] `agents/security-expert/STATUS.md`
- [x] `agents/security-expert/DECISIONS.md`
- [x] `agents/security-expert/OPEN_QUESTIONS.md`
- [x] `agents/security-expert/NEXT_STEPS.md` (this file)
- [x] `agents/security-expert/SKILLS.md`
- [x] `ACCEPTANCE.md` — Security & Compliance section (§3)
- [x] `agents/README.md`, `agents/HANDOFF.md`,
  `agents/DECISIONS.md`, `agents/OPEN_QUESTIONS.md`
- [x] `forum/AGENT-security-opus47-claim.md`
- [x] Append `[SEC]` entries to `docs/agents/decisions.md`,
  `docs/agents/open-questions.md`, `docs/agents/changelog.md`
- [x] Run `scripts/lint.sh` (sanity check; no source changes)
- [x] Open PR, merge

## Up next (priority order)

1. **Audit the in-flight registry endpoint** once it lands on main.
   Specifically:
   - `permissions.is_admin_user` — confirm it short-circuits before
     any model access.
   - `registry.iter_visible_models` — confirm `has_module_permission`
     and `has_view_permission` both gate.
   - `views/registry.RegistryView` — confirm `forbidden_response()`
     for anonymous + non-staff + non-admin-site cases.
   - Confirm tests cover anon, non-staff, staff-no-perm, staff-ok,
     and unregistered model paths.

2. **Add a pre-commit hook config** (`.pre-commit-config.yaml`) with:
   - `gitleaks` for secret scanning
   - `ruff` (already configured)
   - `bandit -q -r django_admin_react`
   - A small custom hook that runs `git diff --cached | grep -E ...`
     for token patterns matching the regex in `scripts/lint.sh`.
   Document in `SECURITY.md` and `CONTRIBUTING.md` how to enable
   pre-commit locally.

3. **Threat model doc** (`docs/threat-model.md`):
   - One STRIDE pass per endpoint group (registry, list, detail,
     create, update, delete).
   - Map each finding to an invariant in `agents/security-expert/AGENT.md`.

4. **Write `tests/test_security.py`** as a centralised home for
   security regression tests (anonymous, non-staff, unregistered
   model, sensitive-field-not-serialized, CSRF-missing, readonly-
   field-not-writable, excluded-field-not-writable). Each endpoint
   PR adds rows to it.

5. **Dependency-audit workflow** (`scripts/audit-deps.sh`):
   - `poetry run pip-audit`
   - `pnpm audit --prod`
   - Fail on `severity ≥ high`.
   Add to `scripts/lint.sh` once stable; for now run on demand.

6. **Release hardening checklist** (`docs/release.md`) when v1 nears:
   - Tag must be signed.
   - `pyproject.toml` version bumped, not `0.0.0`.
   - PyPI token in env, not in file.
   - `scripts/build.sh` + `scripts/deploy.sh` runs only by human.
   - Post-release: GitHub Release notes, SBOM attached.

7. **CSP / clickjacking / cookie hardening recommendation snippet**
   for `docs/installation.md` (deferred until the Architect agent
   has signed off on the installation doc structure).

## Always-on duties

- Skim `git log origin/main..HEAD` for security-relevant changes
  on every session start.
- Watch for any new dependency in `pyproject.toml` or
  `frontend/package.json` — that triggers a dependency audit.
- Watch for any new `urls.py` patterns that mount publicly.
- Skim forum/ for `[SEC]`-tagged threads.
