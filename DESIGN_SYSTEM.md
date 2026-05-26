# Design system

Owner: Product / UX role.
Implementing role: Frontend Engineer agent — see open Issues on the
[Project board](https://github.com/users/MartinCastroAlvarez/projects/3).
Last reviewed: 2026-05-25.

> The design system is **opinionated, closed, and small**. The point
> is not to give us range — it's to make every screen consistent for
> a Django developer who never touched React.

If a screen needs a token that does not appear here, propose an
addition via [`docs/agents/open-questions.md`](docs/agents/open-questions.md)
rather than inventing a one-off.

---

## 1. Principles

1. **Less is more.** One scale, one set of tokens, one style of focus
   ring. Tailwind's default escape hatches are fine for prototyping;
   shipped code uses tokens from this document.
2. **Predictable beats clever.** Linear / Notion / GitHub feel:
   sober, neutral, fast. No gradients, no shadows beyond elevation
   `sm`, no decorative iconography.
3. **Dark mode is first-class.** Every token has a light and a dark
   value. Dark mode is not "inverted light" — see §3.
4. **Accessibility is part of the design**, not a polish step.
   Contrast and focus rings are pinned in this file; designers can
   tune hues but not relax these.
5. **Theming is opt-in via CSS variables**, not via React props or
   build-time swaps. See §10.

---

## 2. Tokens — the source of truth

All tokens are exported as CSS variables on `:root` for light and on
`.dark` for dark mode. Tailwind utilities reference them via
`colors.dar.*` in `tailwind.config.js`. Authors **must** use the
Tailwind utility, not the variable directly, except for one-off
overrides.

### 2.1 Color — surface scale

| Token       | Light          | Dark             | Use                                                  |
| ----------- | -------------- | ---------------- | ---------------------------------------------------- |
| `bg`        | `#ffffff`      | `#0b0d10`        | Page background.                                     |
| `bg-subtle` | `#f7f8fa`      | `#11141a`        | Card backgrounds, table zebra.                       |
| `bg-muted`  | `#eef0f4`      | `#171b22`        | Form-field background, hover for non-primary rows.   |
| `border`    | `#e3e6ec`      | `#222732`        | Default borders, dividers.                           |
| `border-strong` | `#c7ccd6`  | `#3a414f`        | Focus borders, emphasised dividers.                  |

### 2.2 Color — text scale

| Token         | Light       | Dark        | Use                                          |
| ------------- | ----------- | ----------- | -------------------------------------------- |
| `text`        | `#0b0d10`   | `#f3f4f7`   | Primary text. Min contrast 7:1 vs `bg`.      |
| `text-muted`  | `#525866`   | `#9aa1b0`   | Secondary text (timestamps, helper text).    |
| `text-subtle` | `#7b8294`   | `#727a8a`   | Tertiary text (placeholders, disabled).      |
| `text-invert` | `#ffffff`   | `#0b0d10`   | Text on filled `accent` backgrounds.         |

### 2.3 Color — semantic accents

Closed set. Adding a new accent requires a `docs/agents/decisions.md`
entry.

| Token        | Light hue (600) | Dark hue (400) | Use                                              |
| ------------ | --------------- | --------------- | ------------------------------------------------ |
| `accent`     | `#3553f5`       | `#7e9bff`       | Primary buttons, links, focus rings.             |
| `success`    | `#1f8a4f`       | `#5dd3a0`       | Saved / created confirmations.                   |
| `warning`    | `#a76800`       | `#f0bd6b`       | Cautionary banners, "this is destructive".       |
| `danger`     | `#c1352f`       | `#ff7f78`       | Delete buttons, validation errors.               |

Hover, active, and disabled states are derived by Tailwind's
opacity / shade modifiers from these base values. **Designers do not
ship custom hover hues.**

### 2.4 Spacing — 4-pt grid

`0, 1, 2, 3, 4, 6, 8, 12, 16, 24` (multiply by 4 for px). Tailwind's
default `space-x-*` and `gap-*` values map 1:1. No half-step values.
No negative margins outside table cell collapses.

### 2.5 Radii

| Token        | Value | Use                                           |
| ------------ | ----- | --------------------------------------------- |
| `radius-sm`  | 4 px  | Inputs, table corners.                        |
| `radius-md`  | 6 px  | Buttons, badges.                              |
| `radius-lg`  | 10 px | Cards, dialogs.                               |

### 2.6 Elevation

| Token          | Light                                        | Dark                                       | Use                       |
| -------------- | -------------------------------------------- | ------------------------------------------ | ------------------------- |
| `shadow-sm`    | `0 1px 2px rgb(0 0 0 / 0.06)`                | `0 0 0 1px rgb(255 255 255 / 0.06)`        | Cards, table rows hover.  |
| `shadow-md`    | `0 4px 12px rgb(0 0 0 / 0.08)`               | `0 4px 12px rgb(0 0 0 / 0.6)`              | Dropdowns, command palette.|
| `shadow-lg`    | `0 8px 24px rgb(0 0 0 / 0.10)`               | `0 8px 24px rgb(0 0 0 / 0.7)`              | Modal dialogs.            |

No `xl`, no `2xl`. If you need more depth, the layout is wrong.

### 2.7 Typography ladder

| Token        | Size / line height | Weight | Use                                |
| ------------ | ------------------ | ------ | ---------------------------------- |
| `text-xs`    | 12 / 16            | 500    | Table column headers, badges.      |
| `text-sm`    | 13 / 20            | 400    | Body, form labels, table cells.    |
| `text-base` | 14 / 22            | 400    | Detail page descriptions.          |
| `text-md`    | 16 / 24            | 500    | Page section titles.               |
| `text-lg`    | 18 / 26            | 600    | Page title.                        |
| `text-xl`    | 22 / 30            | 600    | Reserved (empty-state hero).       |

Font stack:

```css
font-family:
  ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Inter",
  "Helvetica Neue", Arial, sans-serif;
```

System fonts only. No webfont loading.

Monospace (code, IDs):

```css
font-family:
  ui-monospace, SFMono-Regular, "JetBrains Mono",
  "Cascadia Mono", "Menlo", monospace;
```

### 2.8 Focus ring

A single style for the entire SPA:

```
outline: 2px solid var(--accent);
outline-offset: 2px;
border-radius: inherit;
```

No "focus-visible only when keyboard" exceptions; we always show the
ring. It is visible against both `bg` and `bg-subtle` (contrast ≥
3:1, verified per §4).

### 2.9 Motion

| Token            | Value                              | Use                                  |
| ---------------- | ---------------------------------- | ------------------------------------ |
| `duration-fast`  | 120 ms                             | Hover transitions, button presses.   |
| `duration-base`  | 160 ms                             | Modal / drawer enter / exit.         |
| `easing-out`     | `cubic-bezier(0.16, 1, 0.3, 1)`    | Default for in / out animations.     |

Any animation longer than 200 ms must be justified in code review.
All animations respect `@media (prefers-reduced-motion: reduce)`:
`duration: 0ms` and no `transform` interpolation.

---

## 3. Dark mode

Dark mode is not light mode with inverted colours. Specifically:

- **Backgrounds get a slight blue cast** (`#0b0d10`, `#11141a`)
  rather than pure neutrals. Pure black causes halation in OLED
  displays at the contrasts we hit.
- **Saturated accents are desaturated by ~20 %** in dark mode (use
  the 400-shade column in §2.3, not the 600-shade).
- **Borders gain 1–2 px more contrast** to remain visible against the
  shifted background.

Authoring rule: write Tailwind classes once (`bg-bg`, `text-text`,
`border-border`). Mode swap happens via CSS variables — components
do not branch on `dark:` for tokens already in the table above.

Mode source of truth (priority order):

1. Explicit user toggle (persisted to localStorage `dar:v1:theme`).
2. `prefers-color-scheme` from the OS.
3. Light.

First-paint flash is **not acceptable** (criterion A-7 in
[`ACCEPTANCE.md`](ACCEPTANCE.md)). A tiny inline script at the top of
`<body>` reads the persisted preference and sets a class on the
`<html>` element before the first React render.

---

## 4. Accessibility minimums

These are pinned in code review. Designers may **not** relax them.

- **Color contrast.** ≥ 4.5:1 for normal text; ≥ 3:1 for ≥ 18 pt or
  bold ≥ 14 pt; ≥ 3:1 for focus rings and UI components against
  adjacent colours.
- **Touch targets.** ≥ 44 × 44 px on touch devices.
- **Keyboard.** Everything reachable via `Tab`; everything actionable
  via `Enter` / `Space` (and `Esc` to dismiss).
- **Reduced motion.** Respected per §2.9.
- **Focus management.** When a route changes, focus moves to the
  first heading on the new screen.
- **Live regions.** Loading / saved / error announcements use
  `role="status"` (polite) for non-critical and `role="alert"`
  (assertive) for failures.

Detailed acceptance in [`docs/ux/accessibility.md`](docs/ux/accessibility.md)
(filed alongside the design system).

---

## 5. Component primitives

The closed set in `@dar/ui`. Each one has fixed variants — composing
new variants in page packages is not allowed.

| Primitive       | Variants                                           | Notes                                              |
| --------------- | -------------------------------------------------- | -------------------------------------------------- |
| `Button`        | `primary`, `secondary`, `ghost`, `danger`, sizes `sm`/`md` | Loading state via spinner inside; never inline. |
| `IconButton`    | Same variants                                      | 44 × 44 px hit area on touch.                      |
| `Input`         | `text`, `email`, `url`, `password`, `number`       | Error state via `aria-invalid` + red border.       |
| `Textarea`      | One variant                                        | Auto-grow to content, capped at 12 rows.           |
| `Select`        | Native `<select>` styled, with custom arrow        | No fancy combobox in v1.                           |
| `Checkbox`      | One variant                                        | Label on the right, 44 × 44 px hit on touch.       |
| `Switch`        | One variant                                        | For booleans where the page hint reads better as on/off. |
| `Badge`         | `neutral`, `success`, `warning`, `danger`          | For status pills only; no decoration.              |
| `Table`         | One variant                                        | Sticky header, zebra rows on `bg-subtle`.          |
| `Pagination`    | One variant                                        | Prev / next / jump-to-page; uses URL `page` param. |
| `Toast`         | `success`, `warning`, `danger`                     | Top-right; auto-dismiss 4 s; AA contrast.          |
| `Dialog`        | One variant                                        | Focus trap, `Esc` to close, restores focus.        |
| `Drawer`        | One variant                                        | Right-side, mobile-friendly version of Dialog.     |
| `Skeleton`      | Sizes mirror `Input`, `Table`, `Card`              | Replaces spinners on first load *and* on route transitions. Never carries text — no "Loading…" inside the skeleton. |
| `EmptyState`    | One variant                                        | Hero + helper text + optional CTA.                 |
| `ErrorState`    | One variant                                        | "Couldn't load this"; retry CTA.                   |

Anything not in this table requires a `decisions.md` entry to add.

---

## 6. Layout

Three layouts only:

1. **Shell.** Sidebar (registry navigation) + main content. Sidebar
   collapses to a top sheet at < 1024 px (tablet) and a drawer at
   < 640 px (phone).
2. **Page.** Title, breadcrumb, primary action button(s), content
   slot. All pages use this shell.
3. **Form.** Single column at < 1024 px; two columns at ≥ 1024 px
   for short fields (boolean, foreign key); always single column for
   text areas and rich fields. Fieldsets are visually grouped via
   `Card`.

Max content width: **1280 px**. Anything wider feels like a spreadsheet,
not an admin.

---

## 7. Iconography

- Use **Lucide** icons (open-source MIT). One icon library. No emoji
  in shipped UI.
- Stroke width 1.5. Size 16 px in body, 20 px in buttons, 18 px in
  table action cells.
- Icons must be paired with text or `aria-label` — never icon-only
  without an accessible name.

---

## 8. Loading / empty / error / optimistic states

See [`docs/ux/states.md`](docs/ux/states.md) for full specs. In short:

- **Loading.** Skeletons matching the final layout — including route
  transitions (sidebar click swaps the table to a skeleton on the
  same tick, Slack-style). Spinner only for in-progress button
  actions. The strings "Loading", "Fetching", "Please wait" and
  similar are banned from the SPA UI; see
  [`docs/ux/states.md`](docs/ux/states.md) §1 "Banned copy".
- **Empty.** `EmptyState` primitive: friendly title, one-line
  explanation, optional CTA. Never a blank screen.
- **Error.** `ErrorState` primitive: short message, retry button,
  link to docs if applicable. Stack traces are for `DEBUG=True` only
  and live in the response body, never in the UI.
- **Optimistic.** On user-initiated mutations the UI updates
  immediately, debounced flush via `@dar/data` ([`docs/data-layer.md`](docs/data-layer.md));
  rollback + toast on rejection.

---

## 9. Voice and tone in UI strings

- **Imperative for actions.** "Save", "Delete", "Add account".
- **Past tense for confirmations.** "Account saved.", "Item deleted."
- **No "Are you sure?"** for low-stakes actions. Confirm dialogs are
  reserved for delete and other destructive paths.
- **No exclamation marks.** Even on success. "Saved." is enough.
- **No anthropomorphism.** Don't say "Oops" or "Uh-oh". Say what
  failed.
- **No marketing.** No "powered by", "made with love", "magic".

---

## 10. Theming (consumer customisation)

The supported customisation surface is intentionally tight. The
**full extensibility contract** (including actions, inlines,
detail blocks, and custom HTML) lives in
[`docs/ux/extensibility.md`](docs/ux/extensibility.md); this
section is only the **theming** slice (X-1 in that contract).

- **CSS variables override (recommended).** Consumers point
  `DJANGO_ADMIN_REACT["theme_css"]` at a static CSS file. The
  package serves it before our bundle, so CSS-variable
  re-assignments — `--dar-accent`, `--dar-bg`, `--dar-radius-md`,
  etc. — win the cascade. Editing the file and reloading the
  page applies the change **without rebuilding the SPA and
  without restarting Django** (mapped to `ACCEPTANCE.md` §2.9
  E-5a).
- **Tailwind config extension** (advanced). A consumer who builds
  from source can extend `tailwind.config.js` to add or recolour
  classes. Documented under "fork your bundle" — only required
  for shape / token changes the CSS-variable surface doesn't
  cover.

Out of scope:

- **Full config replacement** (no extension, just override). v1
  cannot guarantee components keep working — closed for the
  foreseeable future.
- **Runtime theme swaps** beyond light / dark.

---

## 11. Anti-patterns

- Inventing a one-off `bg-blue-50` instead of a token.
- Reaching into `@dar/ui` from a page package to "tweak" a button —
  open a PR to add a variant instead.
- Using shadows beyond `sm`/`md`/`lg`.
- "Just for this one screen…". No.
- Hard-coding hex colours in components. Use the Tailwind utility.
- Toast spam. Toasts are for unsolicited feedback, not for every
  click.

---

## 12. Cross-references

- [`PRODUCT_VISION.md`](PRODUCT_VISION.md) — what we're building and why.
- [`ACCEPTANCE.md`](ACCEPTANCE.md) §2.5 / §2.8 — accessibility and
  visual consistency criteria.
- [`docs/ux/accessibility.md`](docs/ux/accessibility.md) — AA checklist.
- [`docs/ux/states.md`](docs/ux/states.md) — loading / empty / error /
  optimistic.
- [`docs/ux/responsive.md`](docs/ux/responsive.md) — breakpoint table.
- [`docs/data-layer.md`](docs/data-layer.md) — how optimistic UI works
  under the hood.
