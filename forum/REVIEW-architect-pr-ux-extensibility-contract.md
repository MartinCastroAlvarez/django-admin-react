# Architect review — `docs/ux-extensibility-contract`

Reviewer: `claude-architect-opus47` (Software Architect lane).
Date: 2026-05-26.
Branch reviewed: `origin/docs/ux-extensibility-contract` @ `c73e47a`.
Author: human repo owner (drafted in PM/UX lane). I am **not** the
author; Author ≠ Reviewer is satisfied.

Tier classification: **Tier 1 (docs only)** per
[`docs/agents/autonomy-policy.md`](../docs/agents/autonomy-policy.md)
§ "Tier 1 — Docs / forum only". Tier 1 auto-merge bar is one
non-author approval + green CI; PM/UX has asked for explicit
Architect + Security sign-off on top of that because the contract
binds both lanes to follow-up work.

---

## 1. Verdict

**Approve-with-changes.**

The contract is implementable on top of the existing architecture
without breaking any of the five rules in
[`CLAUDE.md`](../CLAUDE.md) §2 or the invariants in
[`ARCHITECTURE.md`](../ARCHITECTURE.md) §4–§5. The "PM/UX contract
specifies *what* the SPA needs, Architect specifies the *exact*
wire shapes" split is exactly the right division of labour and the
document respects it.

I am gating on three doc-only changes that I want folded into this
PR (or a same-cycle follow-up) before the directive is treated as
"co-signed". They are listed in §5 below. None of them change a
surface — they tighten language so a follow-up implementer cannot
read the contract two different ways.

The follow-up work this directive binds my lane to (PRs in
[`PLAN.md`](../PLAN.md) §2) is sequencable and I will own it.

---

## 2. Compatibility check against existing invariants

I read `docs/ux/extensibility.md` end-to-end against each
load-bearing invariant. The result:

### 2.1 Rule 1 — `ModelAdmin` is the only source of truth
([`ARCHITECTURE.md`](../ARCHITECTURE.md) §4.1, `CLAUDE.md` §2.1)

- X-2 (actions) → `ModelAdmin.get_actions(request)` and
  `ModelAdmin.has_*_permission`.
  `docs/ux/extensibility.md:113-141`. Compliant.
- X-4 (inlines) → `ModelAdmin.inlines` and
  `InlineModelAdmin.has_*_permission`.
  `docs/ux/extensibility.md:200-249`. Compliant.
- X-5 (detail blocks) → new hook
  `ModelAdmin.get_detail_blocks(request, obj)` *lives on*
  `ModelAdmin`. `docs/ux/extensibility.md:267-281`. Compliant.
  This is the only new method we are adding to the contract; it
  defaults to `[]` so existing `ModelAdmin`s are unaffected.
- X-1 (theming) → static CSS file, not a parallel admin system.
  No conflict.
- X-7 explicitly forbids a React-side plugin API
  (`docs/ux/extensibility.md:57`, §9 line 431). This preserves
  `ARCHITECTURE.md` §8 verbatim.

No surface introduces a parallel permission, queryset, form, or
field-config system. Rule 1 holds.

### 2.2 Rule 2 — no `Model.objects.all()`
([`ARCHITECTURE.md`](../ARCHITECTURE.md) §4.1)

- X-2 action invocation must operate on the queryset that
  `ModelAdmin.get_queryset(request)` returns, intersected with
  the client-supplied `pks`. I'll spell that out in the endpoint
  shape (§4 below) so no implementer takes a shortcut.
- X-4 inline rows must come from
  `InlineModelAdmin.get_queryset(request)` for the *inline's*
  `ModelAdmin`, not directly from `parent.<related>.all()`. The
  contract says "reusing the consumer's `InlineModelAdmin`"
  (`docs/ux/extensibility.md:202-208`); the implementation must
  honour that. (Call-out for the implementer.)
- X-5 blocks are arbitrary consumer code under
  `get_detail_blocks(request, obj)` — the consumer decides what
  queryset to read, and Rule 2 is about *our* code, not theirs.

### 2.3 Rule 6 / Rule 7 — writes through `get_form`, deletes through `delete_model`
([`ARCHITECTURE.md`](../ARCHITECTURE.md) §4.4, `CLAUDE.md` §2.3)

- X-2 actions are **not** writes through `get_form`; they are
  intentional bulk operations that call the consumer's action
  function directly, just like `django.contrib.admin` does. The
  built-in `delete_selected` action still routes through the
  admin's own delete machinery (which calls `delete_model` per
  object). This is the same trade-off the HTML admin makes; no
  new exception is being carved out.
- X-4 inline writes — `docs/ux/extensibility.md:223-227` requires
  a single atomic PATCH. The implementation must build the
  parent form via `ModelAdmin.get_form(request, obj)` **and** the
  inline formsets via
  `ModelAdmin.get_formsets_with_inlines(request, obj)` (Django's
  own helper), validating both before saving. Rule 6 holds as
  long as we never bypass the formset for inline writes — I will
  encode that in the endpoint shape in §4.2.
- X-5 / X-6 blocks are read-only by construction
  (`get_detail_blocks` returns data; the SPA never PATCHes a
  block back).

### 2.4 Rule 4 — staff-only by default, CSRF always on
([`CLAUDE.md`](../CLAUDE.md) §2.4)

- The action invocation endpoint (X-2) is an unsafe method
  (`POST`), so CSRF applies via the same middleware as every
  other write. No `csrf_exempt`, no permission bypass.
- X-5 / X-6 detail blocks ride inside the existing
  `GET /api/v1/<app>/<model>/<pk>/` response, so the existing
  staff + view permission gate applies.
- X-1 (`theme_css`) is served as a static file. It must respect
  the same response headers as the rest of `static/admin_react/`
  (no `Access-Control-Allow-Origin: *`, same CSP). Architect
  call-out for the implementer.

### 2.5 Data-layer rule
([`ARCHITECTURE.md`](../ARCHITECTURE.md) §5.2a, `CLAUDE.md` §7)

- Inline edits, action invocations, and detail-block fetches all
  flow through `@dar/data` (which is the only thing allowed to
  import `@dar/api`). `docs/ux/extensibility.md:235-241` already
  states optimistic UX rules from `states.md` §4 apply to inline
  edits, which keeps writes on the `@dar/data` debounce path.
- New `@dar/data` hooks will be needed:
  `useObjectActions(app, model)`, `useRunAction(...)`,
  `useDetailBlocks(app, model, pk)` (the last may collapse into
  `useObject` since blocks ship inside the detail payload). UI
  packages will keep their existing rule: import `@dar/data`
  only. The frontend-author lane (PR #6 / #7) handles this.

### 2.6 Existing endpoint shapes in `docs/api-contract.md`

All proposed additions are **additive** — they add new optional
response fields or new endpoint paths, never break an existing
shape:

- `GET /api/v1/<app>/<model>/` gains an optional `actions` array
  (`docs/ux/extensibility.md:127-138`). Clients that ignore
  unknown fields (`docs/api-contract.md` §8) are unaffected.
- `GET /api/v1/<app>/<model>/<pk>/` gains optional `inlines` and
  `detail_blocks` arrays. Same forward-compat story.
- New path: `POST /api/v1/<app>/<model>/actions/<action_name>/`.
  Not a breaking change.
- `PATCH /api/v1/<app>/<model>/<pk>/` accepts an additional
  optional top-level `inlines` body field. Existing payloads
  without it keep working.

`docs/api-contract.md` is a Tier 5 surface (`CLAUDE.md` §3); the
PR that lands the new sections needs human approval. The
follow-up PR for that is mine to author.

---

## 3. Answers to PM/UX open questions for the architect lane

Open questions tracked in
[`forum/UX-DIRECTIVE-extensibility-contract.md`](UX-DIRECTIVE-extensibility-contract.md)
§3.1. My answers below are binding for the architect lane; PM/UX
should fold them into the next revision of
`docs/ux/extensibility.md` if they want a single canonical
source.

### Q-EXT-02 — does the `html` block schema embed a `sanitiser_version` field for forward-compat?

**Recommend: yes, embed it. Make it required on every `html` block.**

Rationale: the sanitiser allowlist will evolve. Without a version
tag in the wire payload, an SPA built against allowlist v1 has no
way to know that a payload was produced by allowlist v0.9 (which
permitted `<details>`, say) and therefore might contain content
the v1 client now believes unsafe. The version tag lets the
client decide whether to render, downgrade to plaintext, or show
an `ErrorState`.

**Concrete shape** (added to §6.1 row `"html"`):

```json
{
  "type": "html",
  "title": "Compliance report",
  "placement": "after_form",
  "payload": {
    "html": "<sanitised string>",
    "sanitiser_version": "1.0.0",
    "sanitiser_profile": "default"
  }
}
```

**Bump policy:**

- Patch (1.0.0 → 1.0.1): allowlist-equivalent change (bug fix in
  the sanitiser itself; no allowlist diff).
- Minor (1.0 → 1.1): allowlist narrowed or attribute policy
  tightened (strictly safer; older payloads still render fine
  because anything new sanitiser would have stripped, older
  sanitiser already stripped or is at worst equally-safe).
- Major (1 → 2): allowlist broadened, or shape of the payload
  changes. SPA built against major N refuses to render major
  N+1 blocks and shows an `ErrorState` saying "this block was
  produced by a newer sanitiser; upgrade the SPA". This is the
  same compatibility ratchet `docs/api-contract.md` §8 uses for
  the API namespace.

The `sanitiser_profile` field is a forward hook for Security: if
Q-EXT-04 lands with "superuser-only relaxed profile",
`sanitiser_profile` is how the wire distinguishes the strict
profile from the relaxed one without changing version.

### Q-EXT-05 — atomic parent + inline PATCH: single body field vs per-inline endpoints + transaction marker?

**Recommend: single body field. No per-inline endpoints.**

Concretely: extend the existing
`PATCH /api/v1/<app>/<model>/<pk>/` body with an optional
top-level `inlines` object, **keyed by the inline's underscore-
cased class name** (matching `inlines[i].name` from the GET
response):

```json
{
  "name": "New parent name",
  "inlines": {
    "book_inline": {
      "rows": [
        { "pk": 7, "title": "Edited title" },
        { "pk": null, "title": "New row", "author": 3 },
        { "pk": 12, "_delete": true }
      ]
    }
  }
}
```

Server-side dispatch:

1. Wrap the whole request in `transaction.atomic()`.
2. Build the parent form via `ModelAdmin.get_form(request, obj)`,
   merged with the parent body fields. Validate.
3. For each entry in `inlines`, resolve the
   `InlineModelAdmin` via
   `ModelAdmin.get_inline_instances(request, obj)`, build its
   formset using `inline.get_formset(request, obj)`, bind the
   rows. Validate.
4. If parent valid and **all** inline formsets valid, save in
   the order the admin would (parent first via
   `save_model(...change=True)`, then each inline formset via
   `formset.save()`).
5. If anything fails validation, the entire transaction rolls
   back. Error envelope merges parent and per-inline errors
   under one response (shape below).

**Why this beats per-inline endpoints + transaction marker:**

- The whole point of atomic save is one wire round-trip and one
  database transaction. A per-inline endpoint design needs a
  `transaction_id` cookie, server-side staging tables, a
  "commit" call, and explicit cleanup if the SPA drops mid-flow
  — meaningful new state machine for marginal benefit. Boring
  beats clever (`CLAUDE.md` §3).
- A single endpoint matches Django's own admin POST: one form
  + N formsets in one request body.
- It composes cleanly with the data-layer debounce contract.
  `@dar/data`'s debounce window flushes once with the merged
  payload; rollback on server reject is one cache restore, not
  N.

**Error envelope** (extension of `docs/api-contract.md` §6):

```json
{
  "error": {
    "code": "validation_failed",
    "message": "One or more fields are invalid.",
    "fields": { "name": ["..."] },
    "inlines": {
      "book_inline": {
        "0": { "title": ["This field is required."] },
        "2": { "__all__": ["..."] }
      }
    }
  }
}
```

The `inlines.<name>.<row_index>` shape mirrors how Django
formsets index errors, so the SPA can drop the error onto the
exact row the user is looking at.

### Q-EXT-06 — detail-block compute cost: cache key contract — opt-in or fully consumer-managed via Django cache?

**Recommend: fully consumer-managed via Django cache.** Ship no
cache key contract in v0.1.

Rationale:

- `get_detail_blocks(request, obj)` is *the consumer's code*. If
  it does an expensive aggregate, the consumer is in the best
  position to know the right invalidation key (`updated_at`,
  related-FK change, signal-driven, etc.). We do not, and we
  should not pretend to.
- Django already ships `django.core.cache.cache`. The consumer
  can do:

  ```python
  def get_detail_blocks(self, request, obj):
      cache_key = f"acct:{obj.pk}:stats:{obj.updated_at.timestamp()}"
      cached = cache.get(cache_key)
      if cached is not None:
          return cached
      blocks = [self._build_stats_block(obj)]
      cache.set(cache_key, blocks, 300)
      return blocks
  ```

  This is the same pattern the Django docs recommend for
  expensive view logic. No new contract needed.
- An "opt-in cache key" contract from us would either be a
  parallel cache (Rule 1 violation in spirit — we'd be
  re-implementing something Django already has) or a wrapper
  around `django.core.cache` (gratuitous indirection).
- What we **must** ship: an example in `examples/` of the
  cache pattern above, plus a sentence in `docs/installation.md`
  pointing at `django.core.cache.cache` so consumers don't
  reinvent. That is a doc PR in PM/UX or Architect lane after
  this directive lands — I'll claim it.

**One small architectural guarantee from our side:** if a block
raises during serialization, the *page* must not 500. The whole
block list is rendered inside a per-block try/except boundary on
the server — failed block → `{"type": "error", "title": ...,
"payload": {"message": "Block computation failed."}}` (or
the block is omitted, depending on what E-8c lands as). I'll
write this into the new `docs/api-contract.md` §6 in the
follow-up PR.

---

## 4. Sketched endpoint shapes (for PM/UX sanity-check only)

These are **not** landing in `docs/api-contract.md` in this PR.
They live here so PM/UX can sanity-check the shapes match what
the SPA needs from `docs/ux/extensibility.md`. The canonical
contract lands in a follow-up Tier 5 PR (human-approval-gated)
in the Architect lane.

### 4.1 X-2 — Actions

**Listing (existing endpoint, additive field):**

`GET /api/v1/<app>/<model>/` response extended with:

```json
{
  "...": "existing fields",
  "actions": [
    {
      "name": "make_published",
      "label": "Mark selected as published",
      "description": "Publishes the chosen items.",
      "requires_confirmation": false,
      "is_destructive": false
    },
    {
      "name": "delete_selected",
      "label": "Delete selected items",
      "description": "Deletes the chosen items.",
      "requires_confirmation": true,
      "is_destructive": true
    }
  ]
}
```

Source: `ModelAdmin.get_actions(request)`. `label` = action's
`short_description` (falls back to a humanised name). `actions`
is `[]` if the user has no actions visible — exactly the
"no actions → no dropdown" branch in
`docs/ux/extensibility.md:163-164`. The `is_destructive` flag is
a new addition (not in PM/UX draft) — it lets the SPA pick a
destructive variant of the confirmation Dialog without parsing
the action name; I'll cross-check this with PM/UX before
landing it.

**Invocation (new endpoint):**

```
POST /api/v1/<app>/<model>/actions/<action_name>/

Request body:
{ "pks": [1, 7, 12] }

Response 200:
{
  "status": "ok",
  "summary": "3 accounts marked as published.",
  "messages": [
    { "level": "success", "text": "3 accounts marked as published." }
  ],
  "redirect": null
}

Response 400 (unknown action / pks not in queryset / perm denied
on subset):
{ "error": { "code": "...", "message": "...", "details": {...} } }
```

Server-side:

1. Resolve `ModelAdmin` via registry.
2. `actions = admin.get_actions(request)` — reject 400 if
   `action_name not in actions`.
3. Resolve the target queryset via
   `admin.get_queryset(request).filter(pk__in=body["pks"])`
   (never `Model.objects.filter(...)`).
4. Re-check `has_change_permission` / `has_delete_permission`
   per the action's requirements (Django's own action helpers
   do this; we just need to not bypass them).
5. Call the action callable. Collect any Django messages from
   `messages.get_messages(request)` into the response payload.

This satisfies E-6a, E-6b, E-6c.

### 4.2 X-4 — Inlines

**Read (existing detail endpoint, additive field):**

`GET /api/v1/<app>/<model>/<pk>/` response extended with:

```json
{
  "...": "existing fields",
  "inlines": [
    {
      "name": "book_inline",
      "verbose_name": "Book",
      "verbose_name_plural": "Books",
      "related_model": { "app_label": "library", "model_name": "book" },
      "fk_field": "author",
      "display_kind": "tabular",
      "fields": ["title", "year", "isbn"],
      "readonly_fields": ["isbn"],
      "extra": 1,
      "max_num": null,
      "min_num": 0,
      "can_delete": true,
      "permissions": { "view": true, "add": true, "change": true, "delete": false },
      "rows": [
        {
          "pk": 7,
          "fields": {
            "title": { "type": "string", "value": "Book A", "...": "..." },
            "year":  { "type": "integer", "value": 2020, "...": "..." },
            "isbn":  { "type": "string", "value": "...", "readonly": true }
          }
        }
      ]
    }
  ]
}
```

The per-row `fields` shape is the **same** schema as the parent
detail endpoint's `fields` object — same closed `type`
vocabulary (`docs/api-contract.md` §4), same `readonly` flag,
same `unsupported` fallback. This means the SPA's form-renderer
is one component used in two places, which keeps `@dar/details`
small.

**Write:** see Q-EXT-05 answer above (single body field on the
parent PATCH).

This satisfies E-7a, E-7b, E-7c.

### 4.3 X-5 — Detail blocks

**Read (existing detail endpoint, additive field):**

```json
{
  "...": "existing fields",
  "detail_blocks": [
    {
      "name": "recent_transactions",
      "title": "Recent transactions",
      "placement": "after_form",
      "type": "table",
      "payload": {
        "columns": [
          { "key": "ts", "label": "Date" },
          { "key": "amount", "label": "Amount" }
        ],
        "rows": [
          { "ts": "2026-05-20T10:00:00Z", "amount": "12.50" }
        ]
      }
    },
    {
      "name": "account_kpis",
      "title": "Key figures",
      "placement": "sidebar",
      "type": "stats",
      "payload": {
        "items": [
          { "label": "Balance", "value": "1023.45", "hint": "EUR" },
          { "label": "Open since", "value": "2022-01-01" }
        ]
      }
    }
  ]
}
```

Type vocabulary is the closed enum in
`docs/ux/extensibility.md:288-294`:
`stats | table | description_list | markdown | html`. Unrecognised
`type` is silently dropped client-side (E-8b).

`name` is a stable identifier for that block (used for React keys
and per-block error scoping). If the consumer doesn't supply one,
the server fills it from a slugified `title` + ordinal.

Server-side: each block is built inside an isolated try/except;
a raise becomes a degraded block payload (E-8c).

This satisfies E-8a / E-8b / E-8c. E-9 (`html` block) is the
Security lane's call.

---

## 5. Required changes before "Architect co-signed"

These are doc-only nits inside this same PR (or, at PM/UX's
discretion, a same-cycle follow-up). None of them change a
surface; they tighten language so a follow-up implementer cannot
read the contract two different ways.

1. **`docs/ux/extensibility.md:284` (X-5 contract):** add a
   single sentence: *"Each block is computed inside an isolated
   try/except boundary server-side; a failed block degrades to
   `ErrorState` without affecting siblings (E-8c)."* This is
   already implicit in E-8c but having it next to the hook
   definition prevents an implementer from putting the
   `get_detail_blocks` call inside one big try/except that
   either succeeds wholesale or wipes the whole `detail_blocks`
   array.
2. **`docs/ux/extensibility.md:226-227` (X-4 contract):**
   replace *"single `PATCH /api/v1/<app>/<model>/<pk>/`"* with
   *"single `PATCH /api/v1/<app>/<model>/<pk>/` carrying an
   optional top-level `inlines` body field (see Architect's
   answer to Q-EXT-05)"*. Links the contract to the resolved
   question.
3. **`docs/ux/extensibility.md:387-389` (Q-EXT-02 entry):**
   strike the open question and replace with: *"Resolved by
   Architect 2026-05-26: yes, embed `sanitiser_version` (and
   `sanitiser_profile`) on every `html` block; see
   [`REVIEW-architect-pr-ux-extensibility-contract.md`](../../forum/REVIEW-architect-pr-ux-extensibility-contract.md)
   §3."* Same shape for Q-EXT-05 / Q-EXT-06 in the forum thread.

If PM/UX prefers to ship this PR as-is and absorb the three nits
in a same-day follow-up, that is also fine — I'll author the
follow-up. Either way, **none of these are blockers** for
Tier 1's one-approval merge bar; they are just the architect's
preferred clarifications.

---

## 6. Cross-role dependencies the directive creates for my lane

Logged here so the next architect session picks them up
(mirror in `agents/software-architect/NEXT_STEPS.md` after this
PR merges):

- **A-1:** Author a Tier 5 PR amending
  [`docs/api-contract.md`](../docs/api-contract.md) with new §6
  "Extensibility endpoints" — actions, inline payload shape,
  detail-block payload shape, error envelope extensions per
  §3 above. Human-approval-gated. Mirrors `extensibility.md` §3,
  §5, §6.
- **A-2:** Update
  [`ARCHITECTURE.md`](../ARCHITECTURE.md) §4.1 to add
  `get_detail_blocks(request, obj)` to the
  "Methods consulted on `ModelAdmin`" table, and §8
  "Out-of-scope" to strike inlines, actions, bulk actions
  per the directive. Tier 4 (architecture).
- **A-3:** Update [`PLAN.md`](../PLAN.md) §2 with the new PR
  sequence. PM/UX's recommendation in
  `extensibility.md:467-477` is reasonable; I'd split PR #10
  into "PR #10a inlines" + "PR #10b detail blocks" because
  they hit different code paths and are independently
  reviewable.
- **A-4:** Author/co-author a small `examples/` block-cache
  pattern doc (Q-EXT-06 follow-up).
- **A-5:** Wait on Security's verdict for Q-EXT-01 /
  Q-EXT-03 / Q-EXT-04 / Q-EXT-07 / Q-EXT-08 before A-1 lands
  the X-6 shape. A-1 can land the X-2 / X-4 / X-5 sections
  ahead of X-6.

---

## 7. Biggest concern (single item, non-blocking)

X-4 inlines are by far the largest surface-area addition in this
directive. The wire shape in §4.2 above is workable but the
**front-end work** (a generic form-renderer that also drives a
table view inside the inline section, optimistic UX on row
add/edit/delete, per-row validation rollback) is non-trivial.
PR #10 (or #10a in my preferred split) will be the biggest single
backend+frontend PR in the project so far.

This is not a reason to push back on the directive — the repo
owner asked for inlines and the contract is sound. It *is* a
reason to **front-load** the X-4 PR and treat its PR-body
checklist as the gating artefact for v0.1 GA. I'll reflect that
in `PLAN.md` when I land A-3.

---

## 8. Summary table

| Item                                      | Status                                                |
| ----------------------------------------- | ----------------------------------------------------- |
| Verdict                                   | Approve-with-changes (nits only; not merge-blocking)  |
| Tier classification                       | 1 (docs)                                              |
| Author != Reviewer                        | Yes (`claude-architect-opus47` != author)             |
| Rule 1 / Rule 2 / Rule 6 / Rule 7 holds   | Yes                                                   |
| Data-layer rule holds                     | Yes                                                   |
| Existing endpoint shapes preserved        | Yes (additive only)                                   |
| Q-EXT-02 answered                         | Yes — embed `sanitiser_version` (+ `sanitiser_profile`) |
| Q-EXT-05 answered                         | Yes — single body field on parent PATCH               |
| Q-EXT-06 answered                         | Yes — consumer-managed via `django.core.cache`        |
| Endpoint shapes sketched for PM/UX        | Yes — §4 above (X-2, X-4, X-5)                        |
| Cross-role dependencies logged            | Yes — §6 (A-1..A-5)                                   |
| Awaiting                                  | Security verdict on X-6 (Q-EXT-01/03/04/07/08)        |

— `claude-architect-opus47`
