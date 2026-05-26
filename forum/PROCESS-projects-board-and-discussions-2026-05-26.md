# Process change — GitHub Projects + Discussions (2026-05-26)

Two adjacent process changes that take effect together:

1. **Live status moves to a GitHub Projects board.**
2. **Part of `forum/` migrates to GitHub Discussions** ahead of the
   repository going public.

This note explains what moves where, what stays put, and why.

---

## 1. GitHub Projects — "django-admin-react roadmap"

- URL: <https://github.com/users/MartinCastroAlvarez/projects/3>
- Custom fields: `Priority` (P0 / P1 / P2), `Area`
  (Backend / Frontend / Docs / Security / DX / Infra), `Phase`
  (v0.1 / v0.2 / v1.0 / Later).
- Three views: **Board** (group by Status), **Table** (sort Priority
  → Phase), **Roadmap** (group by Phase).

### What now lives on the board

- The PR sequence currently scattered across `PLAN.md §2`,
  `PROGRESS.md`, `docs/pm-acceptance-status.md`, and the
  pseudo-status fragments in various `forum/REVIEW-*.md` files.
- The 12 functional-gap issues filed by the production-Django pilot
  (`#54`–`#65`) and the docs PR (`#66`), with initial Priority / Area
  / Phase assignments based on the consumer triage.
- Future PR work — every PR claims a card before opening.

### What does NOT live on the board

- The *narrative* parts of `PLAN.md` — why this order, what
  assumptions, what was rejected. These belong in markdown because
  the board's field values cannot carry argument.
- `ACCEPTANCE.md` — the formal spec text. Per-criterion live status
  (✅ / ⏳ / ❌) is best derived from the board.
- `ARCHITECTURE.md`, `SECURITY.md`, `CLAUDE.md`, `docs/api-contract.md`,
  `docs/threat-model.md`. Design contracts stay markdown.

### Workflow contract

- An agent (or human) **claims a board card** before opening a PR.
  This replaces the per-PR `AGENT-<id>-<slot>-claim.md` files for
  *future* PR slots. Existing claim files in `forum/` are historical
  and stay.
- When the PR opens, link the card to the PR; the board's "linked
  PRs" column reflects the live status of work.
- When the PR merges, the board's "Done" column is the running
  changelog.

---

## 2. Forum → Discussions migration

GitHub Discussions is now enabled. The forum is partially
migrating — *partially*, because some of what lives in `forum/`
genuinely belongs in git-resident markdown, not in an external
threaded UI.

### Moves to Discussions

| Category | What | Why |
|---|---|---|
| **Announcements** | Release notes, process changes (like this one), heads-up posts | Notification surface is built-in; broadcasts are timestamped |
| **Q&A** | "How do I integrate this with X?" / "Is the API stable yet?" | Threaded answers, accepted-answer marker, search |
| **Ideas** | Pre-issue brainstorming (a feature idea that isn't ripe enough to be an issue yet) | Lighter weight than an issue; converts to an issue when scoped |
| **Show & Tell** | Consumer demos, screenshots, integration walkthroughs | Community engagement surface |

The existing pattern of **role-based PR reviews** in `forum/`
(`REVIEW-architect-*`, `REVIEW-pm-*`, `REVIEW-security-*`) moves to
**inline PR review comments** on the PR itself. The reviews are
about a specific diff; the PR review surface is built for that.

### Stays in `forum/`

| File pattern | Why it stays in git |
|---|---|
| `AGENT-<id>-claim.md` / `AGENT-<id>-counterclaim.md` | These claim a *file scope* before edits. Git is the authoritative record of who touched what; the claim file lives next to the code it claims. Moving to Discussions breaks that locality. |
| `AGENT-<id>-status-<date>.md` | Status updates are read by future agent sessions starting a new branch — they're part of the agent's required-reading set per `CLAUDE.md §0`. A Discussions thread is not. |
| `RESOLVED-<topic>.md` | Post-mortems and incident notes — durable, append-only, cross-linkable from `docs/agents/decisions.md`. |
| `UX-DIRECTIVE-*`, `ARCHITECT-*`, `SECURITY-*-cycle.md` | Multi-PR coordination artifacts that span several reviews; better as one file than scattered threads. |
| `CONSUMER-feedback-*.md` | Consumer-integration feedback drops. The detailed requirements live in `docs/consumer/`; the forum entry is the announcement that links them. |

### Open-source-readiness scan

Before the repo flips to public, a forum-content scan caught two
items worth noting:

- **Two pre-existing files reference `martin-castro-laminr-ai`**
  (the gh-CLI-authed account name) in the context of GitHub-auth
  troubleshooting:
  - `forum/AGENT-claude-foundation-status-02.md` (lines 33, 47)
  - `forum/AGENT-opus47-pr03-registry-claim.md` (lines 74, 77)
  The username is already public on GitHub (it appears on every
  commit and PR), so this is a low-severity disclosure. Recommend
  redacting to `<gh-cli-account>` since the username adds no value
  to the historical context preserved.
- **One file mentions "transcripts"** — `forum/AGENT-security-opus47-pypi-deploy-gate.md`
  line 101 — context is "matches in transcripts" referring to
  grep-test fixtures, not chat-log paste. Safe.

Everything else came back clean: no email addresses, no Shortcut
story IDs, no Slack channel IDs, no internal URLs, no tokens, no
secret-shaped strings. The `fintech` / `library` / `ecommerce`
mentions across forum files refer to the package's own
[`examples/`](../examples/) directory and are the *intended* public
vocabulary.

### Migration steps

1. Land this commit (adds this process note and the
   `docs/agents/decisions.md` entry).
2. Optional cleanup PR: redact `martin-castro-laminr-ai` →
   `<gh-cli-account>` in the two AGENT files. Owner: whoever flips
   the repo to public.
3. Repo goes public.
4. Open the four Discussions categories above.
5. Pin one Discussions post per category with a short charter so the
   first-time contributor knows where things go.

---

## 3. Cross-references

- ADR entry: `docs/agents/decisions.md` → 2026-05-26 row.
- `CLAUDE.md §0` will pick up a one-line pointer to the board so new
  sessions land on the board *before* opening `PLAN.md`.
- `PLAN.md §2` retains the narrative; the per-slot "claimed by" /
  "status" columns are now superseded by the board.

— posted from a production Django integration pilot, 2026-05-26
