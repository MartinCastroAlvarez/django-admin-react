# Decisions

Append-only log of accepted architectural decisions. Each entry: date,
one-line summary, link to the PR or thread where it was decided.

Newest decisions on top.

---

## 2026-05-27 — Reconcile S-5: delegation-only auth shells are in scope

Security lane (`claude-security-opus47-2026-05-27`). `ACCEPTANCE.md` S-5
originally read "the package does **not** ship login views, password
reset, ... or any auth flow." But the React-login feature already shipped
(`views/auth.py` — `LoginView`/`LogoutView`, PRs #167/#168/#120), and the
password-set endpoint lands here (`views/password.py`, Issue #252). The
old S-5 *test* only ever checked view **filenames**, so `auth.py` (stem
"auth") slipped through — it was guarding a loophole, not the invariant.

- **[SEC] S-5 reconciled.** The invariant is restated as "no parallel
  auth **mechanism**": no OAuth, no JWT issuance, no custom credential
  hashing or token minting. The package **may** expose thin JSON entry
  points that **delegate** to Django's own auth — `authenticate` /
  `login` / `logout` / `AdminPasswordChangeForm` / `user.set_password`.
  The S-5 test is now content-based
  (`test_s5_no_parallel_auth_mechanism_in_views`): it fails if any view
  references `jwt`/`oauth` or mints credentials itself (`make_password`,
  `set_unusable_password`, `jwt.encode`, `secrets.token_*`,
  `create_access_token`, `itsdangerous`). This is a **Tier-5** change
  (security contract + auth-adjacent code) — flagged for human /
  cross-agent review on the PR; not auto-merged.

---

## 2026-05-26 — Promote QSEC-05 to a decision (session timeout recommendation)

Security lane (`claude-security-opus47-2026-05-26-pm`) sweep of the
Security-lane tentative directions in
[`open-questions.md`](open-questions.md). One direction has been
de-facto adopted in `SECURITY.md`; promoting tightens the
open-questions list.

- **[SEC] QSEC-2026-05-25-05 → adopted.** Session expiration nudge
  is **documentation-only** in `SECURITY.md` §9 "Recommended consumer
  settings". The package never overrides `SESSION_COOKIE_AGE`; the
  README example pins it at `60 * 60 * 8` (8h staff session) with
  the `# QSEC-05` provenance comment so the source of the
  recommendation stays traceable. No runtime check, no setting in
  `DJANGO_ADMIN_REACT`, no Django-level monkey-patch — anything
  beyond a documented recommendation would be an opt-in feature
  separate from this decision.

QSEC-2026-05-25-01 (rate limiting), QSEC-2026-05-25-02 (audit
logging via `LogEntry`), QSEC-2026-05-25-03 (CSP defaults for the
SPA shell), and QSEC-2026-05-25-04 (SRI on the bundle) remain open
— none has shipped the code or doc surface their tentative
directions describe.

---

## 2026-05-26 — Promote five Architect-lane tentative directions to decisions

Architect lane (`claude-architect-opus47-2026-05-26-2`) sweep of
[`open-questions.md`](open-questions.md). Each tentative direction
below has been de-facto adopted in code or rendered obsolete by a
merged PR; promoting tightens the open-questions list to what's
actually open.

- **[ARCH] Q-2026-05-25-01 → A.** Do not depend on `djangorestframework`.
  Confirmed: `pyproject.toml` runtime dependencies = `python, Django` only
  (M-7 in `ACCEPTANCE.md` §3.3). Hand-rolled serialization in
  `api/serializers.py`. Revisit only if hand-rolled becomes a
  maintenance burden.
- **[ARCH] Q-2026-05-25-02 → A.** Single-site v1. `django_admin_react/conf.py`
  resolves `ADMIN_SITE` as a single dotted-path string; multi-site
  (a list of dotted paths) is a v1.x topic.
- **[ARCH] Q-2026-05-25-04 → A.** Bundle delivery via Django staticfiles,
  no WhiteNoise runtime dep. Consumer chooses their static-files strategy
  (collectstatic + nginx, WhiteNoise, or another). Confirmed: zero
  runtime deps added.
- **[ARCH] Q-2026-05-25-05 → obsolete.** M2M is no longer a read-only
  stub; [PR #107](https://github.com/MartinCastroAlvarez/django-admin-react/pull/107) shipped read+write with `filter_horizontal` /
  `filter_vertical` widget propagation. `ACCEPTANCE.md` §2.9 E-11
  carries the live shape.
- **[PM × ARCH] Q-2026-05-25-CX-01 → A.** `mount` is request-derived
  (reconstructed from `request.path` in `django_admin_react/views.py:109`,
  surfaced via the `<meta name="dar-mount">` tag the SPA reads). PR #120
  hardened the SPA-side `detectMount()` to honour the meta. Consumers
  behind path-stripping proxies set `FORCE_SCRIPT_NAME`. No
  `MOUNT_OVERRIDE` settings key — minimum-configuration principle.

Q-2026-05-25-03 (frontend test runner: Vitest vs Jest) remains open —
no frontend test PR has landed yet, so the first one confirms the
direction. QSEC-2026-05-25-01..05 (Security-lane open questions) stay
open pending the Security session's own promotion.

---

## 2026-05-26 — Status tracking moves to GitHub Projects; forum migrates partially to Discussions

- **[PROCESS] Live status is on the GitHub Projects board.** The
  project at <https://github.com/users/MartinCastroAlvarez/projects/3>
  ("django-admin-react roadmap") is now the single source of truth
  for what's in flight, what's blocked, and what's planned. Custom
  fields: `Priority` (P0/P1/P2), `Area`
  (Backend/Frontend/Docs/Security/DX/Infra), `Phase` (v0.1/v0.2/v1.0/
  Later). The PR list + issue list are the changelog by attribution.
- **[PROCESS] Markdown stays the source for the *why*.**
  The driving Issues + Project board cards carry the why for each work item;
  `ACCEPTANCE.md` keeps the spec text. `ARCHITECTURE.md`, `SECURITY.md`,
  `CLAUDE.md`, `docs/api-contract.md`, `docs/threat-model.md` —
  unchanged, still markdown. The board shows *what*; the docs explain
  *why*; the issues say *how*.
- **[PROCESS] Forum partially migrates to GitHub Discussions.**
  Announcements and open questions move to Discussions (categories:
  Announcements, Q&A, Ideas, Show & Tell). Per-PR reviews move to PR
  review comments. The claim / counter-claim / status-update pattern
  moved to Discussions / Issues / PR comments; the `forum/` folder has been retired.
  Migration plan: [Discussion #71](https://github.com/MartinCastroAlvarez/django-admin-react/discussions/71).
- **[PROCESS] Consumer feedback drops are recorded under
  `docs/consumer/`.** One markdown file per integration round,
  generic and anonymized, cross-linking the matching GitHub issues.
  First entry: `docs/consumer/requirements-pilot-2026-05-26.md`.

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
  reads `AGENT.md` and resumes from there. (STATUS / NEXT_STEPS were retired into the Project board + Issues.) — `docs/agents/README.md`,
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
  both are deferred. (deferred — tracked on the project board)
  *→ SUPERSEDED: M2M read+write shipped (PR #107, Issue #55) and
  autocomplete shipped (Issue #97). See `ARCHITECTURE.md` §8 and the
  obsolete-marker at Q-2026-05-25-05 above.*
- **The PyPI artifact ships pre-built React assets.** Consumers do not
  need Node to install. — `ARCHITECTURE.md` §5.4
- **Forum + docs/agents split.** Forum for ephemeral coordination,
  docs/agents for durable decisions / questions / changelog. — `CLAUDE.md` §3, §4
- **Folder rule: every folder has a `README.md`.** — `CLAUDE.md` §1
- **v1 is small.** Inlines, custom actions, bulk actions, custom widgets,
  autocomplete, raw_id, and the React extension API are explicitly
  deferred. (deferred — tracked on the project board)
  *→ PARTIALLY SUPERSEDED: inlines (#54), custom actions (#101), bulk
  actions (#103), autocomplete / raw_id (#97), and the React panel
  extension surface (#111) have since shipped. Custom widgets and
  runtime theme/config swapping remain the only v1 non-goals. See the
  reconciled `ARCHITECTURE.md` §8 (Issue #237).*

---

> Append future decisions above the next horizontal rule, newest on top.
> Each entry should be one to two lines max. Link out for detail.
