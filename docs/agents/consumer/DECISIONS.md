# Consumer agent — decisions

Append-only log of decisions accepted **by or for the Consumer / Customer
role**. Each entry: date, decision, why, link to PR / Issue / Discussion
that ratified it.

---

## 2026-05-26 — Working-priority order is PRs → Issues → Project → Discussions → ACCEPTANCE

**Decision.** The Consumer agent works the five GitHub surfaces in
fixed priority order at session start:

1. Open Pull Requests (review + merge once 3-role approved).
2. Open Issues (triage + comment + close, file new ones for consumer pain).
3. Project board (reflect state into Projects v2 cards / custom fields).
4. Discussions (long-form threads).
5. `ACCEPTANCE.md` walk-through.

No skipping ahead while an earlier surface still has actionable work.

**Why.** User directive on 2026-05-26: *"when there are PRs opened,
reviewing and approving them is highest priority, so that when the 3
approvals are obtained, they can be merged, next comes ISSUES, and
then comes continuing with the project steps, and looking at the
discussion, and then working towards the acceptance criteria."*

**Ratified by.** This decision, PR (to be linked when this lands).

---

## 2026-05-26 — Consumer findings are filed anonymised

**Decision.** Every Issue, PR comment, Discussion post, or Project
card I produce as the Consumer agent must be written as a generic
Django consumer would write it. No reference to the underlying
consumer application, its model names, brand, internal code names,
or business domain.

**Why.** User directive (multiple repeats across the 2026-05-26
session). The repo is open-source and the public-readable surface
cannot leak any details of the real downstream consumer.

**How to apply.** Before filing, re-read the body and ask: "could a
public reader infer who the consumer is from this?" If yes, rephrase.

**Ratified by.** Standing user instruction.

---

## 2026-05-26 — Coordination is GitHub-native, not `forum/`

**Decision.** All cross-agent coordination happens on GitHub
primitives: PR review comments, Issues, Discussions, Project board.
The Consumer agent does not write to `forum/` (the folder is retired)
or create new markdown threads under `docs/agents/` for ephemeral
state.

**Why.** User directive on 2026-05-26 to migrate off markdown
coordination so the artifact lives where it gets watched, searched,
and notified on. Per `docs/agents/pr-workflow.md` and
`docs/agents/autonomy-policy.md`.

**How to apply.** When tempted to drop a "FYI" markdown file, file
an issue or post a Discussion comment instead. Reserve the
`docs/agents/consumer/` folder for role-durable artifacts (AGENT,
DECISIONS, OPEN_QUESTIONS, SKILLS) only.
