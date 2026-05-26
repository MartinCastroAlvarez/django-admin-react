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

## 9. Acceptance cross-reference

| Topic                | Criterion |
| -------------------- | --------- |
| 375 px usable        | R-1       |
| Table → card         | R-2       |
| Form stacking        | R-3       |
| Touch targets        | R-4       |
| Hover not required   | R-5       |
