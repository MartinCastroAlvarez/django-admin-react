# agents/

Durable, file-based state for each long-running agent role. The repo
is the memory; chat context is volatile and may die at any moment.

If a session dies, a replacement agent of the same role must be able
to read **one** file — `agents/<role>/AGENT.md` — and resume work
exactly where the previous session left off.

## Convention

```
agents/
├── README.md                 # this file
├── DECISIONS.md              # cross-role decisions (shared)
├── OPEN_QUESTIONS.md         # cross-role questions (shared)
├── HANDOFF.md                # active handoffs between roles (shared)
├── product-manager/          # PM / UX Lead role state
│   ├── AGENT.md              # entrypoint — read this first
│   ├── STATUS.md             # current step, blockers
│   ├── DECISIONS.md          # PM-owned decisions
│   ├── OPEN_QUESTIONS.md     # PM-owned open questions
│   ├── NEXT_STEPS.md         # planned next actions
│   └── SKILLS.md             # what this role can/should do
├── software-architect/       # (created by that role)
└── security-expert/          # (created by that role)
```

## Rules

1. **One folder per role.** Roles do not edit each other's folders.
2. **`AGENT.md` is the entrypoint.** Replacement sessions read it
   first and follow the links inside.
3. **No secrets.** Tokens, credentials, .env content, PII never land
   in this tree. If a secret is discovered, document only the
   location and remediation track (see [`SECURITY.md`](../SECURITY.md)
   §5).
4. **Update continuously.** Every meaningful decision, blocker,
   completed step, or new assumption updates the relevant file in
   the same PR (or as a separate doc-only PR if outside a feature PR).
5. **Keep it concise.** Structured markdown with timestamps,
   checklists, links — not narrative prose.
6. **Cross-role coordination** uses the shared files (`DECISIONS.md`,
   `OPEN_QUESTIONS.md`, `HANDOFF.md`) at this folder root.

## Relationship to `docs/agents/`

Two folders exist by design:

- **`docs/agents/`** (existing) — collaboration protocol for one-off
  PRs and ephemeral coordination (PR workflow, autonomy policy,
  change log).
- **`agents/`** (this folder) — durable per-role working state, so a
  fresh session can resume a long-running role.

Decisions of repo-wide architectural significance live in
[`docs/agents/decisions.md`](../docs/agents/decisions.md), with a
back-link from `agents/<role>/DECISIONS.md` when the decision was
made by that role.
