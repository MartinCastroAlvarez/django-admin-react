# Decisions

Append-only log of accepted architectural decisions. Each entry: date,
one-line summary, link to the PR or thread where it was decided.

Newest decisions on top.

---

## 2026-05-25 — Acceptance criteria + durable agent state

- **[SEC] `ACCEPTANCE.md` §4 (Security & Compliance) populated.** 66
  binary criteria (S-1 … S-66) across authn, authz, queryset, write,
  CSRF/session/cookies, serialization, secret hygiene, deps, PII, API
  hardening, logging, release hygiene, and consumer-side secure
  defaults; 8 release-blockers (B-1 … B-8); per-endpoint mandatory
  test matrix. — `ACCEPTANCE.md` §4, `docs/agents/security-expert/`
- **[SEC] Sensitive-field denylist fixed:** `password`, `secret`,
  `token`, `api_key`, `apikey`, `hash`, `private_key`, `session`,
  `nonce`, `salt` — case-insensitive substring match, applied on top
  of admin form `exclude` / `readonly`. — `ACCEPTANCE.md` §4.7 S-31
- **[SEC] Deny-by-default lookup.** Unregistered `app_label` /
  `model_name` / field returns 404, never 400 — prevents enumeration.
  Client-supplied strings resolve only via `admin.site._registry`. —
  `ACCEPTANCE.md` §4.3 S-11/S-12
- **[SEC] CSRF is mandatory.** No `@csrf_exempt` anywhere; missing or
  invalid `X-CSRFToken` on unsafe methods returns 403. SPA shell sets
  the CSRF cookie via Django's middleware. —
  `ACCEPTANCE.md` §4.6 S-26–S-28
- **[SEC] Releases are human-only (tier 6).** `scripts/deploy.sh`
  refuses without `POETRY_PYPI_TOKEN_PYPI` and does not echo it. —
  `ACCEPTANCE.md` §4.13 S-57–S-61
- **`ACCEPTANCE.md` is the production-ready bar.** Sectioned by role:
  §2 PM/UX, §3 Architect, §4 Security, §5 composite release gate.
  Each role owns its own section. Every criterion is binary (yes/no)
  and verifiable by a documented command or file read. Engineering
  §3 has 14 sub-sections + a release-blocking checklist. — `ACCEPTANCE.md`
- **`docs/agents/<role>/` is durable per-role memory.** Distinct from
  `docs/agents/` (which is cross-PR collaboration protocol). Each
  role keeps `AGENT.md` (entrypoint), `STATUS.md`, `DECISIONS.md`,
  `OPEN_QUESTIONS.md`, `NEXT_STEPS.md`, `SKILLS.md`. A fresh session
  reads `AGENT.md` and resumes from there. — `docs/agents/README.md`,
  `docs/agents/software-architect/AGENT.md`
- **Test coverage thresholds codified.** Overall ≥ 90 %;
  `permissions.py` and `serializers.py` at 100 % statements + 100 %
  branches; `views/*` ≥ 95 %. Enforced via
  `--cov-fail-under=90` in pytest. — `ACCEPTANCE.md` §3.5 T-2

---

## 2026-05-25 — Foundation

- **Autonomous PR ops protocol.** Sessions adopt one of Author /
  Reviewer / Merger / Releaser. Auto-merge is gated by tier; tiers 5
  (security/contract surface) and 6 (releases) are always human-only.
  Author ≠ Reviewer ≠ Merger on the same PR. Kill switches:
  `KILL_SWITCH` file, recent edit to `autonomy-policy.md`, back-to-back
  failed CI, open `INCIDENT-*.md`. — `docs/agents/pr-workflow.md`,
  `docs/agents/autonomy-policy.md`
- **Canonical names.** Distribution: `django-admin-react`. Python import:
  `django_admin_react`. `INSTALLED_APPS` entry: `"django_admin_react"`.
  Frontend package prefix: `@dar/*`. No alternate spellings. — `pyproject.toml`, `apps.py`
- **`@dar/data` is the single data layer for the UI.** Page packages
  (`@dar/list`, `@dar/details`, `@dar/models`, `@dar/shell`) read and write
  through `@dar/data` only. `@dar/data` wraps `@dar/api` with React Context
  + `localStorage` (SWR first paint) and debounces user-initiated
  mutations. Direct `@dar/api` imports from page packages are a CI
  failure. — `ARCHITECTURE.md` §5.1, §5.2a; `frontend/packages/data/README.md`;
  full design in [`docs/data-layer.md`](../data-layer.md)
- **MIT license.** Maximally permissive, standard for open-source Python +
  React libraries. — `LICENSE`
- **Package manager: Poetry for Python, pnpm for frontend. No mixing.**
  Mixing managers historically causes silent lockfile drift. — `CLAUDE.md`
- **ModelAdmin is the only source of truth.** No parallel permission,
  registry, queryset, or form contract. — `ARCHITECTURE.md` §4.1
- **Frontend packages: `@dar/ui`, `@dar/api`, `@dar/list`, `@dar/details`,
  `@dar/models`, `@dar/shell`.** Single-responsibility packages avoid the
  "mega-monster" pattern. — `ARCHITECTURE.md` §5.1
- **Settings live under a single optional dict
  `settings.DJANGO_ADMIN_REACT`.** Adding flags one-by-one to `settings.py`
  would explode the consumer's settings file. — `ARCHITECTURE.md` §4.6
- **Mount point is consumer-chosen.** The package never hardcodes
  `/admin/` or `/admin-react/`. — `ARCHITECTURE.md` §4.5
- **CSRF is enforced on every unsafe method. No exemptions.** — `SECURITY.md` §2.6
- **Conservative serializer with `str()` fallback.** Never crash, never
  leak via repr. — `SECURITY.md` §2.7
- **Tailwind theming via CSS variables + config extension. Full config
  replacement is "fork your bundle".** — `ARCHITECTURE.md` §5.3
- **ManyToMany is read-only stub in v1.** Editing requires autocomplete;
  both are deferred. — `PLAN.md` §1
- **The PyPI artifact ships pre-built React assets.** Consumers do not
  need Node to install. — `ARCHITECTURE.md` §5.4
- **Forum + docs/agents split.** Forum for ephemeral coordination,
  docs/agents for durable decisions / questions / changelog. — `CLAUDE.md` §3, §4
- **Folder rule: every folder has a `README.md`.** — `CLAUDE.md` §1
- **v1 is small.** Inlines, custom actions, bulk actions, custom widgets,
  autocomplete, raw_id, and the React extension API are explicitly
  deferred. — `PLAN.md` §1

---

> Append future decisions above the next horizontal rule, newest on top.
> Each entry should be one to two lines max. Link out for detail.
