# docs/agents/ — agent coordination and durable per-role state

This folder is the canonical home for everything an AI agent reading
this repo needs to coordinate with other agents and resume the role
it picks up.

It holds **two kinds of artifact**, side by side:

1. **Cross-PR / cross-session coordination** — protocols, decision
   log, open questions, PR changelog. Append-mostly, public.
2. **Per-role durable state** — one subfolder per long-running role
   (`product-manager/`, `software-architect/`, `security-expert/`).
   The repo is the memory; chat context is volatile. If a session
   dies, a replacement session of the same role reads **one** file —
   `<role>/AGENT.md` — and resumes work exactly where the previous
   session left off.

## Layout

```
docs/agents/
├── README.md             # this file
├── autonomy-policy.md    # tier rules, what's auto-mergeable, kill switches
├── pr-workflow.md        # author / reviewer / merger / releaser protocol
├── changelog.md          # one line per meaningful PR — newest on top
├── decisions.md          # accepted architectural decisions — append-only
├── open-questions.md     # unresolved questions, including cross-role ones
├── handoff.md            # active handoffs between roles
├── product-manager/      # PM / UX Lead role state
│   ├── AGENT.md          # entrypoint — read this first
│   ├── STATUS.md         # current step, blockers
│   ├── DECISIONS.md      # PM-owned decisions
│   ├── OPEN_QUESTIONS.md # PM-owned open questions
│   ├── NEXT_STEPS.md     # planned next actions
│   ├── SKILLS.md         # what this role can/should do
│   └── REVIEW_CHECKLIST.md
├── software-architect/   # Software Architect / Engineering Lead role state
│   └── (same shape as product-manager/)
└── security-expert/      # Security & Compliance Lead role state
    └── (same shape as product-manager/)
```

## When to write where

| You want to…                                          | Write here                              |
| ----------------------------------------------------- | --------------------------------------- |
| Record an accepted, durable design choice             | `decisions.md`                          |
| Surface an unresolved question (single-role)          | `<role>/OPEN_QUESTIONS.md`              |
| Surface an unresolved question (cross-role)           | `open-questions.md` § Cross-role        |
| Note that a PR shipped                                | `changelog.md`                          |
| Record a role-internal decision                       | `<role>/DECISIONS.md`                   |
| Track who is doing what                               | `<role>/STATUS.md` and `<role>/NEXT_STEPS.md` |
| Hand a topic to another role                          | `handoff.md`                            |
| Coordinate ephemerally with another agent             | `/forum/AGENT-*.md`                     |
| Explain how a folder works                            | that folder's `README`                  |
| Document the overall architecture                     | `/ARCHITECTURE.md`                      |

## Per-role folder rules

1. **One folder per role.** Roles do not edit each other's folders.
2. **`AGENT.md` is the entrypoint.** Replacement sessions read it
   first and follow the links inside.
3. **No secrets.** Tokens, credentials, `.env` content, PII never
   land in this tree. If a secret is discovered, document only the
   location and remediation track (see [`../../SECURITY.md`](../../SECURITY.md)
   §5).
4. **Update continuously.** Every meaningful decision, blocker,
   completed step, or new assumption updates the relevant file in
   the same PR (or as a separate doc-only PR if outside a feature PR).
5. **Keep it concise.** Structured markdown with timestamps,
   checklists, links — not narrative prose.
6. **Cross-role coordination uses the shared files at this folder
   root** (`decisions.md`, `open-questions.md`, `handoff.md`).

## What does **not** belong here

- Secrets, tokens, credentials, or `.env` content.
- Long prose that's really architecture — push that into
  `/ARCHITECTURE.md`.
- Transient agent state (use `/forum/`).
- PR text — that belongs in the PR description on GitHub.

## House style

- Dates in ISO format: `YYYY-MM-DD`.
- One-line entries when possible in `changelog.md` / `decisions.md`.
- Sign entries when the author is an agent: `— claude-<role>-<short-id>`.
