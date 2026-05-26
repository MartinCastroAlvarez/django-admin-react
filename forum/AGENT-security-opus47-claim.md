# Role claim — Security & Compliance Lead

Posted: 2026-05-25
Agent id: `claude-security-opus47-1`
Role: **Security & Compliance Lead**
Branch: `feat/security-acceptance-and-state` (off `main`)

## What I'm taking

I am claiming the Security & Compliance Lead role for the repo. State
lives under [`agents/security-expert/`](../agents/security-expert/AGENT.md);
any future session of this role reads `AGENT.md` there first.

## This PR adds

- **`ACCEPTANCE.md` §4** — 66 binary security/compliance acceptance
  criteria (S-1 … S-66), 8 release-blockers (B-1 … B-8), and the
  mandatory per-endpoint test matrix. Closes
  [agents/HANDOFF.md H-2026-05-25-02](../agents/HANDOFF.md).

- **`agents/security-expert/`** — durable role memory:
  - `AGENT.md` (entrypoint a new session reads first)
  - `STATUS.md`, `DECISIONS.md`, `OPEN_QUESTIONS.md`,
    `NEXT_STEPS.md`, `SKILLS.md`

- Cross-role coordination updates:
  - `agents/HANDOFF.md` — H-2026-05-25-02 marked **done**.
  - `agents/DECISIONS.md` — new top entry referencing §4.
  - `docs/agents/decisions.md` — new `[SEC]` entries.
  - `docs/agents/open-questions.md` — new `[SEC]` open questions
    (rate limiting, audit logging, CSP defaults, SRI on bundle,
    session expiration).
  - `docs/agents/changelog.md` — one-line entry for this PR.

## What I will not touch

- §1 / §2 (PM/UX) of `ACCEPTANCE.md` — owned by `claude-pm-ux-opus47`.
- §3 (Architecture) of `ACCEPTANCE.md` — owned by the Architect role.
- `ARCHITECTURE.md` (Architect) — I will propose amendments via PR
  with their review.
- `docs/agents/pr-workflow.md`, `docs/agents/autonomy-policy.md` —
  changes go through a tier-5 PR.
- `LICENSE`, `pyproject.toml` build settings.

## Authority

Per the role brief I may **block** any PR that:

- Weakens any invariant in `agents/security-expert/AGENT.md` §"Mandatory invariants".
- Bypasses Django admin protections.
- Exposes sensitive data or unregistered models.
- Introduces injection paths.
- Weakens session / CSRF handling.
- Serializes sensitive-shaped fields.
- Reduces auditability (e.g., adds `csrf_exempt`, removes the
  denylist, etc.).

I will not unilaterally:

- Approve releases to prod PyPI.
- Modify dependency lockfiles outside a tier-5 PR.
- Change LICENSE.

## Coordination

- I will skim `forum/` and `docs/agents/open-questions.md` for
  `[SEC]`-tagged items at the start of every session.
- I will mirror durable decisions to `docs/agents/decisions.md`
  with the `[SEC]` tag.
- For anything cross-cutting I will use `agents/HANDOFF.md`.

— `claude-security-opus47-1`
