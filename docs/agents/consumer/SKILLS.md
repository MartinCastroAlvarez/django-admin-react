# Consumer agent — operating skills

Practical CLI patterns and heuristics the Consumer agent uses every
session. These are the *muscle memory* the role depends on; the
*role definition* itself is in `AGENT.md`.

---

## 1. Session start: sweep the surfaces in priority order

```bash
# 1. Open PRs needing review
gh pr list --repo MartinCastroAlvarez/django-admin-react --state open \
  --json number,title,headRefName,isDraft,reviewDecision \
  --jq '.[] | select(.isDraft == false)'

# 2. Open issues
gh issue list --repo MartinCastroAlvarez/django-admin-react --state open \
  --json number,title,labels --jq '.[] | .number, .title, [.labels[].name]'

# 3. Project board — show the current "Today" column (or current sprint)
gh project item-list 3 --owner MartinCastroAlvarez --format json \
  --jq '.items[] | {title: .content.title, status: .status, priority: .priority}'

# 4. Discussions — latest threads needing a reply
gh api graphql -f query='{repository(owner:"MartinCastroAlvarez",name:"django-admin-react"){discussions(first:20,orderBy:{field:UPDATED_AT,direction:DESC}){nodes{number title updatedAt}}}}' \
  --jq '.data.repository.discussions.nodes'

# 5. ACCEPTANCE walk — read locally and diff against the shipped surface
cat ACCEPTANCE.md | head -80
```

Do not start at step 5 if step 1 is non-empty. The priority order is
load-bearing.

---

## 2. PR review verdict — substance, not GitHub UI state

Same-login `--approve` is blocked. The autonomy policy
(`docs/agents/autonomy-policy.md` §5) counts the substance of a
review comment, not the GitHub approval state, so post:

```bash
gh pr comment --repo MartinCastroAlvarez/django-admin-react <PR> \
  --body "$(cat <<'EOF'
## 🛒 Consumer / Customer ✅ APPROVE

- Install path: ✓ no new manual steps for consumers.
- Default config: ✓ no new settings required to make it work.
- Error surface: ✓ consumer-facing envelope unchanged / improved.
- Docs co-located: ✓ docs/api-contract.md updated in same PR.
- Anonymisation: n/a (no consumer-pain referenced).

— `consumer-agent`
EOF
)"
```

Replace `✅ APPROVE` with `❌ BLOCK` or `🟡 COMMENT` as needed.

---

## 3. Filing an anonymised consumer-pain issue

Template:

```markdown
**As a Django developer using `django-admin-react`…**

**What I did:** <generic-ised reproduction steps>

**What I expected:** <expectation grounded in `ARCHITECTURE.md` /
`ACCEPTANCE.md`>

**What happened:** <observed behaviour, with envelope / log / stack
*stripped of any consumer fingerprints*>

**Why it matters:** <one-line consumer-impact statement>

---

**Versions:**
- `django-admin-react`: <version>
- Django: <version>
- Python: <version>
- Browser (if SPA): <name + version>
```

Before submitting, run the **anonymisation back-check**:

- [ ] No consumer-app name or brand.
- [ ] No real model / app names from the consumer app.
- [ ] No business-domain wording (rephrased to generic).
- [ ] No infrastructure or deployment detail specific to me.
- [ ] If a sanitised stack trace is attached, it's actually sanitised.

---

## 4. Project board card lifecycle

When a PR I'm reviewing lands:

```bash
# Look up the card for the issue it closes (or the PR itself)
gh project item-list 3 --owner MartinCastroAlvarez --format json \
  --jq '.items[] | select(.content.number == <N>) | .id'

# Move to Done
gh project item-edit --id <ITEM_ID> --field-id <STATUS_FIELD_ID> \
  --single-select-option-id <DONE_OPTION_ID> --project-id <PROJECT_ID>
```

(The exact field/option IDs are stored in the project; resolve them
with `gh project field-list 3 --owner MartinCastroAlvarez`.)

---

## 5. Anonymisation heuristics

When in doubt, rephrase in the **fewest** generic Django primitives
that still let a maintainer reproduce:

- "We hit this in our `<X>` app" → "A consumer-side app exposing a
  custom `ModelAdmin` with `<the relevant overrides only>`."
- "Our `Customer` model" → "A consumer model with a `<field-shape>`
  field".
- "We deploy to `<provider>`" → "We deploy under
  `gunicorn`/`uvicorn`/`runserver`" — choose the **type** of runtime,
  not the brand.
- "Our internal product `<brand>`" → silence. Either the brand is
  load-bearing for the bug (it is not) or it isn't.

The bias is toward **slightly less detail than feels safe**.
