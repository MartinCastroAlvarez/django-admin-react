# Accessibility — WCAG 2.1 AA checklist

`django-admin-react` ships **WCAG 2.1 Level AA** compliance from
v0.1. This file is the auditable checklist.

Maps to [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.5.

---

## 1. Perceivable

| Rule                                          | How we satisfy it                                                  | Verify |
| --------------------------------------------- | ------------------------------------------------------------------ | ------ |
| **1.1.1 Non-text content** has text equivalent | Every `IconButton` has `aria-label`. Decorative icons get `aria-hidden="true"`. | axe-core |
| **1.3.1 Info and relationships** are programmatic | Form labels via `<label for>`. Errors via `aria-describedby`. Tables use `<th scope>`. | axe-core + DOM inspect |
| **1.4.3 Contrast (Minimum)** ≥ 4.5:1 (text) / 3:1 (large/UI) | Token table in [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §2 is verified per release. | Stark / contrast script |
| **1.4.4 Resize text** up to 200 % without loss | Use `rem` / `em` for sizes; no fixed `px` width on text containers. | Manual: browser zoom 200 % |
| **1.4.10 Reflow** — no horizontal scroll at 320 CSS px | Test at 320 px DevTools. | Manual at 320 px |
| **1.4.11 Non-text contrast** ≥ 3:1 for focus rings and UI states | Focus ring uses `accent` against any `bg`/`bg-subtle`. | Stark |
| **1.4.12 Text spacing** survives user CSS overrides | Don't use fixed line-height in pixels. | Manual with user style sheet |
| **1.4.13 Content on hover/focus** dismissible, hoverable, persistent | Tooltips appear on focus too; close on `Esc`. | Manual |

## 2. Operable

| Rule                                          | How we satisfy it                                                  | Verify |
| --------------------------------------------- | ------------------------------------------------------------------ | ------ |
| **2.1.1 Keyboard** — everything reachable     | Custom components use real `<button>` / `<a>`. No `div` with `onclick`. | Keyboard pass |
| **2.1.2 No keyboard trap** (except modals)    | Modals trap focus; everything else releases focus on `Tab` / `Shift+Tab`. | Manual |
| **2.4.1 Bypass blocks** — skip-to-content link | Visible-on-focus skip link at the top of the shell. | Manual + axe |
| **2.4.3 Focus order** is logical              | DOM order matches visual order. Test by tabbing the page. | Manual |
| **2.4.4 Link purpose** clear from text / context | No "click here". Use "Open <Account label>". | Doc review |
| **2.4.6 Headings and labels** are descriptive | Page `<h1>` is "<App> · <Model>"; not "Page". | Spot-check |
| **2.4.7 Focus visible**                       | Universal `2px accent outline` ring (see [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §2.8). | Keyboard pass |
| **2.5.5 Target size (Enhanced)** ≥ 44 × 44 px on touch | Buttons and links have `min-h-11 min-w-11` (44 px). | Audit list |
| **2.5.7 Dragging movements** have non-drag alternative | We don't ship any drag-only interactions in v1. | Code review |

## 3. Understandable

| Rule                                          | How we satisfy it                                                  | Verify |
| --------------------------------------------- | ------------------------------------------------------------------ | ------ |
| **3.1.1 Language of page**                    | `<html lang="…">` set from Django's `LANGUAGE_CODE`. | DOM |
| **3.2.1 On focus** — no unexpected context change | Focus doesn't navigate, submit, or open modals. | Manual |
| **3.2.2 On input** — same                     | Typing into a field doesn't navigate or submit. `Enter` is the explicit submit. | Manual |
| **3.3.1 Error identification** — errors named in text | Field errors as text under the input (not only red border). | DOM |
| **3.3.2 Labels or instructions** present      | Every input has a visible label. | Spot-check |
| **3.3.3 Error suggestion** — when known       | "Username must be unique." not "Invalid input." | Copy review |
| **3.3.4 Error prevention** for delete         | Delete confirms via `Dialog`. Optimistic delete has 10 s "Undo". | Manual |

## 4. Robust

| Rule                                          | How we satisfy it                                                  | Verify |
| --------------------------------------------- | ------------------------------------------------------------------ | ------ |
| **4.1.1 Parsing**                             | Modern React renders valid DOM. We do not nest interactive elements. | axe |
| **4.1.2 Name, role, value** — programmatic    | Use semantic elements; `role` only when extending native semantics. | axe |
| **4.1.3 Status messages**                     | Toasts and save indicators use `role="status"` (polite) or `role="alert"` (assertive failures). | NVDA / VoiceOver pass |

---

## 5. Manual test matrix (every release)

The PM role runs this on the test_project against the example apps.

- [ ] **Keyboard-only walkthrough** — tab from the top of the page
  through every screen; reach every action; submit a form; delete
  an object.
- [ ] **Screen reader pass** — NVDA on Windows + VoiceOver on
  macOS — read the registry, list, detail, error flow.
- [ ] **Zoom 200 %** — no horizontal scroll, no overlapping content.
- [ ] **`prefers-reduced-motion`** — turn on; verify no animations.
- [ ] **`prefers-color-scheme: dark`** — verify no light-mode flash
  on cold load.
- [ ] **High-contrast mode** (Windows) — verify focus rings still
  visible.
- [ ] **`pointer: coarse`** (touch) — verify 44 × 44 targets.
- [ ] **Color-blind passes** — Stark deuteranopia + protanopia +
  tritanopia simulations on the four state colors.

The Merger does not merge a frontend PR until this matrix is green
on the example apps.

---

## 6. Anti-patterns

- `outline: none` on focusable elements without a replacement.
- `aria-hidden="true"` on a focusable element (creates an
  inaccessible element).
- Tooltips on hover only (keyboard users can't reach them).
- Color alone signalling state (use icon + text + color).
- Live regions that announce nothing (`role="alert"` on an empty
  element).
- Custom checkboxes / radios that drop `aria-checked` reporting.

---

## 7. Acceptance cross-reference

| Section here   | Criterion in §2.5  |
| -------------- | ------------------ |
| 1.4.3 / 1.4.11 | A-1, A-2           |
| 2.1.1          | A-3                |
| 2.4.7          | A-1                |
| 3.3.1 / 3.3.2  | A-5                |
| 4.1.3          | A-4                |
| Reduced motion | A-6                |
| `prefers-color-scheme` | A-7        |
