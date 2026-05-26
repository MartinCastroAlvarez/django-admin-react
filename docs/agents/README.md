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
├── decisions.md          # accepted architectural decisions — append-only
├── open-questions.md     # unresolved questions, including cross-role ones
├── product-manager/      # PM / UX Lead role state
│   ├── AGENT.md          # entrypoint — read this first
│   ├── DECISIONS.md      # PM-owned decisions
│   ├── OPEN_QUESTIONS.md # PM-owned open questions
│   ├── SKILLS.md         # what this role can/should do
│   └── REVIEW_CHECKLIST.md
├── software-architect/   # Software Architect / Engineering Lead role state
│   └── (same shape as product-manager/)
└── security-expert/      # Security & Compliance Lead role state
    └── (same shape as product-manager/)
```

Status, progress, work tracking, handoffs, and per-PR review
conversation all live on GitHub now — Issues, the
[Project board](https://github.com/users/MartinCastroAlvarez/projects/3),
Discussions, and PR review comments. The markdown that remains in
this folder is **durable contract** (the role charter, accepted
decisions, open questions) — not status.

## When to write where

| You want to…                                          | Write here                              |
| ----------------------------------------------------- | --------------------------------------- |
| Record an accepted, durable design choice             | `decisions.md`                          |
| Surface an unresolved question (single-role)          | `<role>/OPEN_QUESTIONS.md`              |
| Surface an unresolved question (cross-role)           | `open-questions.md` § Cross-role        |
| Note that a PR shipped                                | The PR itself; merged PR list is the changelog |
| Record a role-internal decision                       | `<role>/DECISIONS.md`                   |
| Track who is doing what                               | Project board card + Issue assignment   |
| Hand a topic to another role                          | Comment on the Issue and re-assign      |
| Coordinate ephemerally with another agent             | Comment on the Issue / PR / Discussion  |
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
- Status / progress / changelog data — the
  [Project board](https://github.com/users/MartinCastroAlvarez/projects/3),
  [Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues),
  and merged PR history are the source of truth.
- Per-PR review conversation — that belongs on the PR itself.
- Announcements / Q&A / community chatter —
  [Discussions](https://github.com/MartinCastroAlvarez/django-admin-react/discussions).

## House style

- Dates in ISO format: `YYYY-MM-DD`.
- One-line entries when possible in `changelog.md` / `decisions.md`.
- Sign entries when the author is an agent: `— claude-<role>-<short-id>`.
