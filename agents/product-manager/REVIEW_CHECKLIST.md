# PM/UX — review checklist

Role-specific checklist the PM/UX agent runs on **every open PR**.
The PM does not own engineering or security review — those belong
to the Architect and Security roles. The PM owns UX, DX, usability,
responsiveness, onboarding, and product consistency.

Source rules: [`agents/DECISIONS.md`](../DECISIONS.md) "Multi-agent
PR review workflow" entry; [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.

---

## 0. Before reviewing

- [ ] `git fetch origin && gh pr checkout <N>` (or pull the branch
      locally).
- [ ] Read the PR description end-to-end. If it doesn't state:
      - the user impact in one sentence,
      - the `ACCEPTANCE.md` §2 criteria it touches,
      - whether it's tier 1/2/3/4 per
        [`docs/agents/autonomy-policy.md`](../../docs/agents/autonomy-policy.md),
      …leave a single comment asking for it and **do not approve
      until it lands**.
- [ ] `bash scripts/lint.sh` locally on the branch. If it fails,
      request changes.

## 1. UX consistency

- [ ] No new visual element exists outside
      [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) primitives.
- [ ] No new color, spacing, or typography token without a
      `docs/agents/decisions.md` entry.
- [ ] No new icon source (Lucide only).
- [ ] No `outline: none` without a documented replacement.
- [ ] Loading / empty / error states use the primitives in
      [`docs/ux/states.md`](../../docs/ux/states.md).

## 2. Responsiveness (only if frontend touched)

- [ ] PR description includes screenshots / clips at **375 px** and
      **1280 px** for any changed screen.
- [ ] Tables collapse to cards at `< 640 px`
      ([`docs/ux/responsive.md`](../../docs/ux/responsive.md) §3).
- [ ] Touch targets ≥ 44 × 44 px on `pointer: coarse`.

## 3. Accessibility (only if frontend touched)

- [ ] Author ran axe-core; report attached to the PR.
- [ ] Keyboard walkthrough described (Tab path documented, focus
      ring visible).
- [ ] `prefers-reduced-motion` respected if motion changed.
- [ ] `prefers-color-scheme` respected for any new color usage.
- [ ] All form errors use `aria-describedby` + text (not colour).

## 4. Onboarding regression (any PR)

- [ ] `pip install` command in README still works.
- [ ] No new required settings key introduced (criterion P-2).
- [ ] No new file under `frontend/` a consumer must edit (D-3).
- [ ] No marketing copy in the README lead 400 words (O-1).

## 5. DX regression (any PR)

- [ ] No `Model.objects.all()` in `django_admin_react/api/`.
- [ ] No new `forms.Form` / `forms.ModelForm` that bypasses
      `ModelAdmin.get_form()`.
- [ ] No "register your model with the React app" step.
- [ ] No new top-level URL added (URL surface is `urls.py` only).

## 6. Documentation hygiene

- [ ] If behaviour changed, the relevant doc in `docs/` was updated
      in the **same** PR.
- [ ] Every new folder has a `README.md`.
- [ ] If an `ACCEPTANCE.md` §2 criterion was added or relaxed, the
      PR is tier 5 and the human reviewer is tagged.

## 7. The "Django dev expectation" test

Read the diff once and ask: "Would a Django developer expect this
behaviour from `django.contrib.admin`?" If no, flag it. If yes,
move on.

## 8. Posting the review

Use one of three GitHub review states:

- **Approve.** Every checkbox above is ✅ and you'd be happy to use
  this in your own project tomorrow.
- **Comment.** You have questions or non-blocking suggestions.
- **Request changes.** At least one checkbox is ❌. Cite the
  specific criterion id (e.g., "P-2 violated by adding
  `DJANGO_ADMIN_REACT['REQUIRED_KEY']`").

**You may not approve a PR you authored or co-authored** (per
[`docs/agents/pr-workflow.md`](../../docs/agents/pr-workflow.md) §1
and the multi-agent workflow decision).

The review **body template**:

```text
## PM/UX review

### Acceptance criteria affected
- §2.x: <criterion id> — pass / fail
- §2.y: <criterion id> — pass / fail

### Concerns
- (or "none")

### Follow-ups
- (or "none")

### Verdict
- approve / request changes / comment
```

## 9. After the review

- [ ] Update [`STATUS.md`](STATUS.md) "Last touched" with the PR
      number and verdict.
- [ ] If you requested changes, add a row to
      [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) only if the issue
      surfaces a *recurring* product question. One-off fixes don't
      need a question.
- [ ] If the review is approve **and** Architect + Security have
      also approved, the PR is mergeable; the **Merger** is a
      separate session (not the PM, not the author).

## 10. Periodic sweep (every session)

- [ ] `gh pr list --state open` — list all open PRs.
- [ ] For each PR with no PM review in the last 24 h: review it.
- [ ] For each PR with merge conflicts: post a comment naming the
      author and asking for a rebase.
- [ ] For each PR with failing local lint: post a comment with the
      first ten lines of the failure.
- [ ] For each PR that has been open > 72 h: add it to
      [`agents/HANDOFF.md`](../HANDOFF.md) as a "stale PR" with the
      author's role and the last activity date.

---

## Anti-patterns when reviewing

- ❌ "LGTM, ship it." — without naming the criteria you checked.
- ❌ Approving a PR that requires a settings change you didn't see
      documented.
- ❌ Requesting changes for taste alone — cite a criterion or a
      `DESIGN_SYSTEM.md` rule.
- ❌ Re-litigating decisions in `agents/DECISIONS.md`. If the
      decision is wrong, open a new entry; don't block the PR.
- ❌ Reviewing engineering code quality — that's the Architect's job.
