# PM open questions — resolutions (2026-05-26)

The four PM open questions tracked in
`docs/agents/product-manager/OPEN_QUESTIONS.md` are resolved below.
Promoting from "tentative" to "decided" reduces open-question debt
and gives engineering agents a stable target to build against.

Each resolution will also be appended to
`docs/agents/product-manager/DECISIONS.md` on the next durable-state
update.

---

## Q-PM-01 — Before / after screenshot pairs in `docs/screenshots/`

**Resolved: superseded.** The repo owner's directive ("real
screenshots, you may use playwright") landed before the React SPA
was ready. The current `docs/screenshots/*.png` set is therefore
"before" (legacy HTML admin) by necessity. When PR #6 / #7 ship,
the same `scripts/screenshots.sh` regenerates an "after" set; the
README can then show a 2 × N grid. **No marketing-driven
"before / after" pairs in the repo** — the grid lives in the README
only, doubled up when both halves exist.

Implication: `docs/screenshots/README.md` §3 stays as-is. The
filename convention does not encode "before / after" — that
distinction lives in the README captions.

---

## Q-PM-02 — Command palette (`cmd+k`) in v0.1 or v1.x?

**Resolved: deferred to v0.2.** v0.1 ships:

- `Tab` / `Esc` / `Enter` / arrow keys.
- `/` to focus the list search.

`Cmd+K` palette work lands in v0.2. Rationale: v0.1 must hit the
`ACCEPTANCE.md` §2.5 accessibility bar first; a palette is polish.

Documented in: `ROADMAP.md` v0.2 row (already says "stretch
command palette" — promote to "in v0.2 scope").

---

## Q-PM-03 — Surface `list_filter` in v0.1?

**Resolved: yes, narrow scope.** v0.1 supports `list_filter` entries
that are:

- `BooleanField`,
- a field with `choices`,
- a `ForeignKey` whose target is small (≤ 25 distinct values; this
  is a UX choice — larger sets demand autocomplete which is v0.2).

Any other filter entry is silently ignored in v0.1; the filter UI
shows the supported ones only, with a footer note "more filter
types in v0.2".

Backend handoff: the list endpoint response in
`docs/api-contract.md` §3 needs a new field
`filters: [{name, label, type, choices?}]`. Filed as
`docs/agents/handoff.md` H-2026-05-26-01 to Architect.

---

## Q-PM-04 — Empty registry CTA when user has zero visible models

**Resolved: friendly message, not redirect.** A staff user who can
view zero models sees the `EmptyState` primitive with:

- Title: "You don't have access to any models."
- Body: "Ask your admin to grant view permissions to at least one
  model."
- CTA: link to the Django docs page on user permissions.

Rationale: redirecting to `LOGIN_URL` would imply the user is logged
out (false). Showing a generic welcome would lie about access. The
honest answer is the friendly empty state, per
`docs/ux/states.md` §2.

Documented in: `docs/ux/states.md` §2 already (this resolution
confirms that doc's tentative direction).

---

## What this changes

- All four open questions move from `OPEN_QUESTIONS.md` to
  `DECISIONS.md` on the next docs/agents/ folder update.
- Q-PM-03 adds a new cross-role handoff to the Architect for the
  filter-options endpoint field.
- `ROADMAP.md` v0.2 row gets a clarification about the command
  palette (low-priority text fix; lands with the next PM batch
  commit).

No engineering work is unblocked by these resolutions alone —
they're product clarifications that prevent future churn.

— `claude-pm-ux-opus47`
