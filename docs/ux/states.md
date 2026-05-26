# Loading / empty / error / optimistic states

Every page in the SPA has four canonical states. Every component in
`@dar/ui` must render each one — there are no "ad-hoc placeholders".

Maps to [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.8 V-4.

---

## 1. Loading

### First load (no cached payload)

- Render a **skeleton** that matches the final layout's outline.
- Use `bg-muted` blocks at the natural sizes (table rows, form
  fields). No spinners.
- The skeleton must appear within the SPA's first frame after
  mount.

### Stale-while-revalidate (`fromCache: true, isStale: true`)

- Render the cached payload immediately.
- Surface a **subtle indicator** that we are refreshing —
  recommendation: a 2-px top bar in `accent` for as long as the
  fetch is in flight.
- Do **not** show a spinner over already-rendered content. The user
  can keep working.

### Route transition (sidebar click → switch model)

This is the canonical "click in the sidebar, swap the table" path.
Reference behaviour is Slack switching channels.

- The route swaps **immediately** — the previous table unmounts on
  the same tick. No "stay on the old screen until the new one is
  ready" delay.
- The new route's frame (header, breadcrumb, action bar, table
  chrome) renders in the first frame with the **`Skeleton`**
  primitive ([`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §5) filling
  the rows.
- Skeleton row count = the last known page size for that model
  (default 25). Column count + widths match the list's
  `list_display`.
- When the cached payload arrives (instant via `@dar/data`'s
  localStorage rehydrate), the skeleton swaps to rows in a single
  frame — no fade, no flicker. The stale-while-revalidate 2-px top
  bar is the only "still loading" signal from that point on.
- If there is no cache for the target model, the skeleton stays up
  until the first network payload resolves.

### In-progress button actions (Save, Delete)

- Replace the button label with a `Spinner` icon + the label kept
  in `aria-label`.
- Disable the button until the request resolves.

### Banned copy

The following strings must never appear in the SPA, in any state,
in any package. Lint rule lives with `@dar/ui`.

- `"Loading"`, `"Loading…"`, `"Loading..."`
- `"Fetching"`, `"Fetching…"`
- `"Please wait"`, `"One moment"`, `"Hang tight"`
- `"Working on it"`, `"Just a sec"`

Reason: the user has told us, on the record, that they do not want
status copy of this shape — they want skeletons. The Skeleton
primitive itself carries no text ([`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md)
§6); aria-live announcements during navigation use
`"<verbose_name_plural> are loading"` only as a screen-reader-only
string, never rendered visually.

### What we never do

- Spinner over the whole screen.
- "Loading…" text inside the table (or anywhere else — see banned
  copy above).
- Layout shift when the real data arrives (skeleton sizes must
  match real sizes ±2 px).
- "Stay on the previous route until the new one is ready" pattern.
  The user clicked the sidebar; the table must change *now*, even
  if the change is a skeleton.

---

## 2. Empty

Use the `EmptyState` primitive ([`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §5).

| Where                         | Copy                                                 | CTA                                          |
| ----------------------------- | ---------------------------------------------------- | -------------------------------------------- |
| Registry, zero models visible | "You don't have access to any models. Ask your admin for view permissions." | Link to Django docs on permissions. |
| List view, zero objects       | "No \<verbose\_name\_plural\> yet."                  | "Add \<verbose\_name\>" — only if `has_add_permission`. |
| Search returns zero           | "No \<verbose\_name\_plural\> match \"\<query\>\"."  | "Clear search" → resets URL `q` param.       |
| Detail view, object missing   | "This \<verbose\_name\> isn't here." (404 path)      | "Back to list".                              |
| Detail view, permission lost  | "You no longer have access to this \<verbose\_name\>." | "Back to list".                            |

Rules:

- Always name the user's resource type (`verbose_name`,
  `verbose_name_plural`). Never generic "items" or "records".
- Never apologise. "Sorry," / "Oops," are banned in copy
  ([`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §9).
- The illustration is **typography only**. No decorative SVG in v1.

---

## 3. Error

Use the `ErrorState` primitive.

### Categories

| Source                                       | Treatment                                                   |
| -------------------------------------------- | ----------------------------------------------------------- |
| Client lost network                          | Inline banner: "You're offline." Optimistic edits keep working. Reconcile on reconnect. |
| Server `5xx`                                 | Page-level `ErrorState` with **Retry** button.              |
| Server `4xx` `validation_failed` on a form   | Field-level errors next to each input (`aria-describedby`). |
| Server `403` `session_expired`               | Re-login modal — see §3.5. Wire-shape per [`docs/api-contract.md`](../api-contract.md) §6.1. |
| Server `403` `forbidden` (no session cookie) | Hard redirect to `LOGIN_URL?next=<current-spa-path>`. The SPA has no cached session to fall back on. |
| Server `403` permission lost mid-flow        | Toast: "You don't have permission anymore." Redirect to list.|
| Server `404` after navigation                | EmptyState ("This isn't here.") with **Back to list**.      |
| Unknown error envelope                       | "Something went wrong. Try refreshing." Plus copy-to-clipboard request ID. |

### What we never do

- Print a stack trace in the UI.
- Hide a failure silently because we have a cached payload.
- Refuse to retry without a page reload.
- Drop the user on a blank page after session loss. The page they
  were on stays rendered behind the re-login modal (§3.5).

---

### 3.5 Session-expiry flow

The SPA's behaviour when the user *was* signed in and now isn't.
Wire shape lives in [`docs/api-contract.md`](../api-contract.md) §10.

#### Detect

Any API response with `error.code === "session_expired"` triggers
the flow. The SPA inspects every response in `@dar/api`; the data
layer (`@dar/data`) routes the event to a global `<SessionGate />`
component mounted at the SPA root.

The SPA does **not** retry the failed request — re-authentication
is the prerequisite, and re-running a write before re-auth would
double-fire on reconnect.

#### Re-login modal

- The modal blocks all other interactions: focus-trapped, scroll-
  locked, `aria-modal="true"`.
- **The page behind it stays rendered** — no white screen, no
  navigation. The user sees their previous state behind the modal.
- Title: "Your session expired".
- Body: "Sign in again to continue. Your work on this page is
  still here." (Reassurance is load-bearing — operators panic
  when admin pages disappear mid-edit.)
- Primary button: **Sign in** → window.location to
  `<LOGIN_URL>?next=<current SPA pathname + search>`.
- No "Cancel" / "Dismiss" — the only path forward is re-auth.

#### After re-login

- Django's login view redirects back to the SPA path from `?next=`.
- The SPA mounts, `@dar/data` hydrates from `localStorage`, then
  revalidates the route's queries against the API.
- Any in-flight optimistic mutations from before the expiry stay in
  `dar:v1:pending:*` and re-flush on the first successful response.
  If a re-flush hits a permission failure, the standard rollback
  flow (§4 step 5) fires.

#### Optional pre-expiry warning

If the consumer sets
`DJANGO_ADMIN_REACT["SESSION_WARNING_SECONDS"] = N` (positive int):

- The SPA polls `GET /api/v1/session/` at most once per minute.
- At `expires_at - N` it shows a non-blocking toast:
  - Body: "Your session expires in `<X minutes>`."
  - Primary button: **Stay signed in** → `POST /api/v1/session/touch/`
    (silently re-stamps `request.session`).
- If the user does nothing, the modal in the previous subsection
  fires when expiry actually lands.

When `SESSION_WARNING_SECONDS` is unset (default), the toast never
appears and the modal is the only signal.

#### Banned copy in this flow

The skeleton-loading banned-copy list from §1 still applies — the
modal must never say "Loading…" while we wait for the redirect.
The "Sign in" button shows a `Spinner` icon while in-flight (the
button-action rule from §1) — never a label change.

#### Acceptance cross-reference

- [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.7 N-5 (updated for the
  modal) + N-6 (the warning-toast row).

---

## 4. Optimistic

For user-initiated mutations through `@dar/data`:

1. **Immediate** — local in-memory state updates synchronously on
   the next React render. `localStorage` is written at the same
   time. The UI feels instant.
2. **Debounced flush** — 300 ms after the last keystroke (per field
   batch). Explicit "Save" / "Delete" / "Add" buttons flush
   immediately (0 ms).
3. **Success** — server payload reconciles silently. No toast for
   every save (toast on Save is for explicit submit actions only).
4. **Validation failure** — rollback the rejected fields, surface
   field-level errors. Keep unrelated edits intact.
5. **Permission / unknown failure** — full rollback for the affected
   object, toast with the error message, drop the `dar:v1:pending:*`
   localStorage entry so we don't retry on reload.

Mappings live in [`docs/data-layer.md`](../data-layer.md) §4.

### When optimistic UI is wrong

- **Delete** — not optimistic. Confirm dialog → request → on success
  remove the row → toast: "Deleted." with an **Undo** button for
  10 s. (Server-side undo is out of scope; "Undo" recreates via the
  cached pre-delete payload as a new object.)
- **Bulk actions** (v1.x) — not optimistic. Confirm with the count.
- **Anything tied to side effects** the consumer's `save_model`
  triggers (emails, payments). Server is the source of truth; we
  show "Saving…" not "Saved" until we hear back.

---

## 5. Combining states

Real screens are mixtures. The list view, mid-search, with a stale
cache, while a row is being deleted:

- Skeleton rows are not used (we have cached rows).
- The 2-px refresh bar is visible at the top.
- The deleted row dims to 50 % opacity until the delete confirms.
- A toast appears on success or rollback.
- The empty state appears only if the **final** result is empty,
  not transiently.

The PM role reviews the **mixed** states in PR review, not only the
canonical singletons.

---

## 6. Acceptance cross-reference

| State                | Criterion              |
| -------------------- | ---------------------- |
| Loading skeletons    | V-4, N-1               |
| Route-transition skeletons (sidebar → table swap) | V-4, N-1, N-2  |
| Empty states         | V-4, O-5, Q-PM-04      |
| Error states         | V-4, N-4, N-5          |
| Session-expiry modal | N-5 (modal flow)       |
| Session-expiry warning toast | N-6            |
| Optimistic flush     | data-layer.md §4       |
| First-paint < 100 ms | N-1, PRODUCT_VISION §7 |
