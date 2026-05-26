# UX principles

The principles below are the lens through which every product
decision is filtered. They are not exhaustive UX laws — they are the
**subset of UX laws that conflict often** in a Django admin and need
explicit tie-breakers.

---

## 1. Match the Django Admin mental model

Django developers already have working models for "admin", "model",
"app", "permission", "staff user", "list view", "change form". The
SPA must use the same vocabulary and the same shapes.

Examples we enforce:

- The sidebar groups models by `app_label` and shows
  `verbose_name_plural`, same as the HTML admin.
- "Add" / "Save" / "Delete" — not "Create" / "Submit" / "Trash".
- Permissions appear as four named gates (view / add / change /
  delete), never as a custom scheme.

Examples we reject:

- "Workspace switcher" (Django has no such concept).
- "Records" / "Entities" instead of "objects".
- "Roles" UI when the consumer's `User` model has groups + permissions.

Maps to acceptance §2.2 D-1, §2.9 E-1.

---

## 2. The cardinal question

> **How would a Django developer expect this to behave?**

If you can't answer without saying "well, in our SPA we…", the
proposal is wrong. Find the Django analogue or drop the feature.

Maps to [`docs/agents/product-manager/SKILLS.md`](../../docs/agents/product-manager/SKILLS.md).

---

## 3. Optimise for the second use, not the first

The first install is exciting and forgiving. The second day, the
user has muscle memory and the slightest friction grates. Optimise
for **repeated use**:

- Keyboard shortcuts where the HTML admin had them
  (e.g., `Esc` to dismiss, `Tab` to traverse, `Enter` to submit).
- Stable URLs (an old bookmark to `/admin/app/model/?q=foo` works).
- Stable button positions across screens (Save bottom-right, not
  re-arranged per screen).

Maps to acceptance §2.7 N-2, N-3.

---

## 4. Latency budget — perception beats benchmarks

A 200 ms paint with skeletons feels faster than a 100 ms paint with
"Loading…". Every screen has a designed first paint:

- **First paint < 100 ms** — render the skeleton from
  `@dar/data`'s `localStorage` hydration.
- **Useful content < 600 ms** — fetched payload reconciles.
- **Interactive < 1500 ms** — interactive controls work.

If a page can't meet this, the page is over-scoped.

Maps to acceptance §2.7 N-1, [`data-layer.md`](../data-layer.md) §3.

---

## 5. Optimistic UI is the default for in-place edits

Form fields update locally before the network responds. The user's
typing is the source of truth; we reconcile on flush.

Reject the proposal "let's disable optimistic UI for X because it
might fail":

- If a write might fail, surface the failure with a `Toast` and a
  one-click "Undo" / "Retry". Don't slow down the 99 % case for the
  1 %.
- Explicit destructive actions (Delete, mass updates) are **not**
  optimistic — they are confirmed (see §6).

Maps to [`docs/data-layer.md`](../data-layer.md) §4.

---

## 6. Confirm only for destruction or expense

Don't ask "Are you sure?" before saving a draft, hiding a field, or
sorting a table. The undo state-of-affairs (Cmd+Z, the page reload,
the form's own validation) is the safety net for most actions.

We **do** confirm for:

- Delete.
- Bulk delete / bulk update (when shipped — v1.x).
- Logout (v1.x — small intercept, since session loss has cascading
  effects across tabs).

Maps to acceptance §2.6 Doc-2 (no faux-cautious copy in the docs
either).

---

## 7. Empty states tell the truth

A user with no permissions sees "You don't have access to any
models", not a marketing welcome screen. A model with no objects
shows the model's column headers and an `EmptyState` row that says
"No <verbose_name_plural> yet" and offers an "Add" CTA only if the
user has `has_add_permission`.

Lying empty states are worse than no UI. Every empty state has been
explicitly designed (see [`states.md`](states.md)).

Maps to acceptance §2.8 V-4, [`docs/agents/product-manager/OPEN_QUESTIONS.md`](../../docs/agents/product-manager/OPEN_QUESTIONS.md) Q-PM-04.

---

## 8. Discoverable, not magical

If a feature exists, the user can find it without reading docs:

- Search visible when `search_fields` is non-empty (otherwise hidden).
- Filters visible when there are filters to apply.
- Pagination always visible when `total > page_size`.
- Help text from `help_text` appears under inputs (no tooltip on
  hover only — keyboard users can't reach it).

If a feature requires you to know it exists, it is not shipped.

---

## 9. Boring beats clever

A button that says "Save" and goes back to the list is correct. A
"Save and add another" button is correct. A "Save with confetti
animation" is not correct.

If a UI element exists in `django.contrib.admin`, copy the behaviour
literally. If it does not exist, default to the **smallest** new
behaviour that solves the problem.

Maps to [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) §3, principle 5.

---

## 10. Reject features that hurt onboarding

A feature that adds a settings key, a new dependency, a new file the
consumer must touch, or a new concept to learn must produce
proportional value. Default answer is **no**.

PM veto applies; see
[`docs/agents/product-manager/AGENT.md`](../../docs/agents/product-manager/AGENT.md) §10.
