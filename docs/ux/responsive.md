# Responsive layout

The SPA is usable down to **375 px wide**. There is no separate
mobile build, no separate mobile route. Same SPA, responsive layout.

Maps to [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.4.

---

## 1. Breakpoints

We use **mobile-first** Tailwind utilities. Names match Tailwind
defaults.

| Name | Min width | Typical device                | Tailwind prefix |
| ---- | --------- | ----------------------------- | --------------- |
| (base) | 0 px    | Small phones (e.g., 375 px)   | (no prefix)     |
| `sm` | 640 px    | Large phones, small tablets   | `sm:`           |
| `md` | 768 px    | Tablets portrait              | `md:`           |
| `lg` | 1024 px  | Tablets landscape, small laptops | `lg:`        |
| `xl` | 1280 px  | Laptops                       | `xl:`           |
| `2xl`| 1536 px  | Large displays                | `2xl:`          |

Targets the SPA must look correct at: **320 / 375 / 414 / 768 /
1024 / 1280 / 1440 / 1920 px**. The Merger spot-checks at 375 /
1024 / 1440 on every frontend PR.

---

## 2. Shell behaviour

| Width        | Sidebar                | Header              | Content max-width |
| ------------ | ---------------------- | ------------------- | ------------------ |
| `< 640 px`   | Hidden; opened via drawer (right-side `Drawer`, focus-trapped). | Compact: hamburger + page title only. | 100 % padding 4 (16 px). |
| `640 – 1023 px` | Same as < 640 px.   | Page title + breadcrumb.                | 100 % padding 6.       |
| `≥ 1024 px`  | Persistent sidebar at 256 px.                                  | Breadcrumb + actions.                    | 1280 px max, centered. |

---

## 3. Table → card collapse

At `< 640 px`, list views render as a vertical list of cards
instead of a horizontal table.

Each card shows:

- The object's `__str__` label as the card title.
- Up to **3** secondary fields from `get_list_display`, in order.
  The rest are accessible by tapping into the detail page.
- The same per-row actions (link to detail; permissions-gated
  delete) collapsed into an `IconButton` row.

Rules:

- The column order in the card mirrors the order in
  `get_list_display`.
- The data-density should be ~1.5 × the desktop row height. Don't
  pack more in.
- Pagination collapses to a single "Load more" button on touch
  devices (`pointer: coarse`).

Maps to R-2.

---

## 4. Form behaviour

| Width        | Form layout                                                      |
| ------------ | ---------------------------------------------------------------- |
| `< 1024 px`  | Single column. Labels above inputs. Help text below.             |
| `≥ 1024 px`  | Two-column layout for booleans, foreign keys, and small choice fields; single column for `Textarea` and any field marked `widget=Textarea`. |

Rules:

- Field groups (`fieldsets`) render as `Card` containers regardless
  of width.
- Required field markers (`*`) are visible AND announced via
  `aria-required`.
- The "Save" button bar sticks to the bottom of the viewport at
  `< 1024 px` so it's always reachable; at `≥ 1024 px` it sits at
  the natural document end.

Maps to R-3.

---

## 5. Touch targets

Minimum **44 × 44 px** for all primary interactive elements when
`pointer: coarse` is detected. `Button` and `IconButton` primitives
satisfy this with `min-h-11 min-w-11` (Tailwind's `11` = 2.75 rem =
44 px at default `font-size`).

Exceptions:

- Inline links inside a paragraph use a 24 × 24 minimum hit-area
  via padding; the link text itself can be smaller.
- Checkbox / radio inputs use a 24 × 24 visible target inside a
  44 × 44 hit area achieved via a `<label>` wrapper.

Maps to R-4.

---

## 6. Hover ≠ required

Every behaviour reachable via hover must also be reachable via
focus and via tap. If a behaviour is only reachable via hover, it
is broken on touch devices.

Examples:

- Row hover that reveals "Delete" → also revealed on focus + tap.
- Tooltip on hover → also on focus.
- Drag handles → out of scope (no drag in v1).

Maps to R-5.

---

## 7. Images, embeds, and overflow

- No fixed-width images in shipped components.
- File preview thumbnails (v1.x — file fields) use `max-width: 100 %`.
- Long tokens in code blocks wrap (we use `overflow-wrap: anywhere`).
- Tables that absolutely must scroll horizontally on desktop get a
  fade-out indicator at the right edge.

---

## 8. Verification

For every frontend PR:

- DevTools responsive mode at **375 / 768 / 1024 / 1440** at minimum.
- No horizontal page scroll at any width.
- All interactive targets pass the 44 × 44 px audit on `pointer:
  coarse`.
- The table → card collapse happens at the documented breakpoint.

Failing any of these is an automatic "Request changes" on the PR.

---

## 9. Creative mobile patterns

Django's HTML admin has no real mobile experience. We do — **the SPA
on a phone should feel like a native admin app**, not a shrunken
desktop page. Tracked under
[issue #85](https://github.com/MartinCastroAlvarez/django-admin-react/issues/85).

Five patterns ship in v0.2. Each maps to a new `ACCEPTANCE.md` §2.4
row (R-6..R-10) lifted when this lands.

### 9.1 Floating Action Button (FAB) — R-6

At `<1024px`, the list page's **Add `<verbose_name>`** button (when
`has_add_permission`) renders as a circular `Button.icon` floating
bottom-right (`fixed bottom-4 right-4`, 56×56 px, `shadow-lg`).
Disappears under the keyboard. At `≥1024px` it sits in the page
header bar as a regular `Button.primary`.

### 9.2 Bottom-sheet detail / inspector — R-7

At `<1024px`, clicking a row pushes a full-screen detail view that
**slides up from the bottom** (250 ms ease-out; 0 ms under
`prefers-reduced-motion`). The shell sidebar is not visible; a
top-left back chevron returns to the list. The list scroll
position is preserved on return.

### 9.3 Pull-to-refresh — R-8

At `<1024px` on touch devices (`pointer: coarse`), the list page
supports pull-to-refresh. The gesture re-runs the list query
against the server (skipping cache). A subtle Skeleton overlay
covers the rows while the request resolves; the chip row (filters
applied) stays visible.

### 9.4 Swipe row actions — R-9

At `<1024px`, swiping a card left exposes the row's
permissions-gated actions:

- **Swipe-left short** (≤80 px) → reveals a `Delete` button (only
  if `has_delete_permission`).
- **Swipe-left long** (full row) → triggers the same Delete
  confirmation flow as the click path. Does not auto-execute.
- **Swipe-right** → reveals contextual actions (`Open`,
  `Duplicate` if applicable). v0.2 ships `Open` only.

A 4-px vertical-only scroll threshold prevents accidental swipes
during scroll. Long-press is reserved for bulk-select (§9.5).

### 9.5 Long-press to enter bulk-select — R-10

At `<1024px`, long-press (≥400 ms) on a card enters bulk-select
mode. The card grows a checkbox indicator, the FAB swaps to an
actions button matching [#58](https://github.com/MartinCastroAlvarez/django-admin-react/issues/58)
(custom admin actions), and the top bar swaps to a count +
"Cancel" button. Mobile-equivalent of the desktop checkbox
column. Exit via Cancel or by emptying the selection.

### 9.6 What we never do on mobile

- **A separate mobile route or build.** Same SPA, same URL, same
  code path. The patterns above are CSS / event-handler branches.
- **Block desktop features on mobile.** Every desktop primary
  flow has a mobile equivalent (FAB ↔ header button, bottom-sheet
  ↔ in-page detail, swipe-delete ↔ row delete, long-press select
  ↔ checkbox select).
- **A "request desktop site" button.** The mobile experience is
  the canonical mobile experience.

### 9.7 Cross-references

- The PWA installability story extends these patterns; installed-app
  behaviour mirrors the responsive web experience in `display:
  standalone`. See [`pwa.md`](pwa.md).
- The skeleton-loading rules ([`states.md`](states.md) §1) apply to
  bottom-sheet pushes too — the sheet shows Skeleton rows on push,
  swaps to real content when the payload resolves.

---

## 10. Acceptance cross-reference

| Topic                  | Criterion |
| ---------------------- | --------- |
| 375 px usable          | R-1       |
| Table → card           | R-2       |
| Form stacking          | R-3       |
| Touch targets          | R-4       |
| Hover not required     | R-5       |
| FAB on mobile          | R-6       |
| Bottom-sheet detail    | R-7       |
| Pull-to-refresh        | R-8       |
| Swipe row actions      | R-9       |
| Long-press bulk-select | R-10      |
