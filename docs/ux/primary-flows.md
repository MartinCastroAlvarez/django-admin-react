# Primary user flows

These are the **release-blocking** user flows for v0.1. They are the
canonical journeys the SPA must execute end-to-end without manual
intervention. The Software Architect scaffolds the E2E test suite
(Playwright or equivalent) against this list.

Owner: Product / UX role.
Cross-refs: [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §3.5 T-5, §2.7,
§2.9; [`states.md`](states.md); [`navigation.md`](navigation.md).

---

## Conventions

Each flow lists:

- **Click-path** — the literal sequence of user actions.
- **Setup** — Django fixtures needed to enable the flow.
- **Assertions** — observable invariants the test must verify.
- **Negative variants** — the failure paths the same flow exercises.

E2E targets run against the test_project + the `examples/library/`
demo app unless stated otherwise — `Author` and `Book` give us a
ForeignKey, a `__str__` label, and a non-trivial `list_display`.

---

## Flow 1 — First-time install and load

Why: this is the cardinal acceptance flow
([`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) §2 step 1-4 and
[`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.1).

### Setup

- Clean Django 5 venv, `django_admin_react` installed.
- `library` example app in `INSTALLED_APPS`.
- One superuser (`root` / known fixture password).
- `library_author` table seeded with **3** rows; `library_book`
  with **5** rows (one per author, plus two with the same author).

### Click-path

1. Visit `/admin-react/`.
2. Server redirects to `LOGIN_URL` (Django admin login) — verified.
3. Log in as `root`.
4. Browser lands on `/admin-react/`.
5. Sidebar lists at least the `library` app.
6. Click "Authors".
7. Click the first row's link to detail.
8. Click "Back" (browser back button).
9. Click the second row's link to detail.

### Assertions

- The first response after login is `/admin-react/` (no extra
  redirect chain).
- `document.title` matches "<app> · <model_name_plural> — Django
  Admin" after step 6 (criterion N-3 / accessibility A-3).
- No full page reloads between steps 6-9 — measured by counting
  `document` requests in the Network panel (criterion N-1).
- Browser back returns the user to the list view with **scroll
  position preserved** (criterion N-2).
- The list page shows the **3** rows; the detail page shows the
  picked author's `__str__` label as the page heading.
- The `mount` field on the registry response equals `/admin-react/`
  (criterion P-4; tests pass at three different mount points).

### Negative variants

- **N1a — anonymous deep link.** Direct visit to
  `/admin-react/library/author/1/` while logged out → redirected
  to `LOGIN_URL?next=/admin-react/library/author/1/`. After login,
  user lands back on the detail page (criterion N-5).
- **N1b — non-staff user.** Log in a non-staff user, visit
  `/admin-react/` → JSON 403 with the canonical envelope (criterion
  O-5).
- **N1c — staff with zero permissions.** Log in staff with no
  `view_*` permissions → the registry empty state appears
  (criterion Q-PM-04 tentative resolution: friendly message, not
  redirect).

---

## Flow 2 — Edit an object end-to-end

Why: the central value proposition is editing data through
`ModelAdmin.get_form()`. This flow exercises optimistic UI, validate
+ save, and the read-after-write reconciliation
([`states.md`](states.md) §4).

### Setup

- Same as Flow 1.
- `library_book` with at least one row whose `title` we will edit.

### Click-path

1. Log in as `root`.
2. Navigate to `library / books`.
3. Click into the first book's detail.
4. Click into the `title` field; type a new value (e.g., "Updated
   title").
5. Wait ≥ 350 ms (debounce window + buffer).
6. Refresh the page.

### Assertions

- The new title appears in the field within **the same render**
  the user typed it (optimistic update; observed via
  `setTimeout(0)` after the input fires).
- The corresponding `localStorage` key
  `dar:v1:detail:library.book:<pk>` contains the new value within
  500 ms of the keystroke.
- Within 500 ms of the debounce window expiring, a `PATCH` request
  hits `/admin-react/api/v1/library/book/<pk>/` and returns 200.
- After refresh, the field still shows "Updated title" (no
  rollback).
- The list view at `/admin-react/library/book/` reflects the
  updated title on the next request.

### Negative variants

- **N2a — server `400 validation_failed`.** Replace `title` with
  the empty string (model enforces non-blank). Within the debounce
  window, the API returns `400` with `{ fields: { title: ["…"] } }`.
  The field shows the error inline; the previous valid value is
  **restored** (criterion D-4); the `dar:v1:pending:*` key is
  dropped.
- **N2b — server `403` mid-edit.** Mid-flow, the user's
  `change_book` permission is revoked via the Django shell. Next
  flush returns `403`. A toast appears; the field's local edit
  rolls back; the page navigates to the list view (criterion N-4).
- **N2c — offline.** Disable the network adapter between step 4 and
  step 5. The keystroke persists in `localStorage`. On reconnect
  the queued `PATCH` flushes and the page reconciles.

---

## Flow 3 — Add, then delete an object

Why: the create + delete paths exercise `ModelAdmin.save_model`,
`ModelAdmin.delete_model`, and the destructive-action confirmation
flow ([`principles.md`](principles.md) §6, criterion E-2 / E-3).

### Setup

- Same as Flow 1.
- An author named "Demo Author" pre-seeded so the new book has a
  valid ForeignKey target.

### Click-path

1. Log in as `root`.
2. Navigate to `library / books`.
3. Click "Add book" (button visible because `has_add_permission` is
   true).
4. Fill in `title = "E2E Test Book"`, pick "Demo Author" in the
   author ForeignKey field.
5. Click "Save".
6. SPA lands on the new object's detail page; URL includes the
   server-assigned `pk`.
7. Click "Delete".
8. Confirm in the dialog.
9. SPA lands on the list view with a toast: "Book deleted." and
   an "Undo" button visible for 10 s.
10. Wait 11 s; toast disappears.

### Assertions

- The "Add book" button is present in step 2 only because
  `has_add_permission` is true; toggling it off hides the button on
  the next request (criterion E-2).
- After step 5, the URL changes to
  `/admin-react/library/book/<new_pk>/` and the list view (when
  navigated back to) contains the new row.
- The new row is **never** assembled client-side from the form
  payload — the SPA renders from the server's `POST` response
  (criterion D-2, D-4).
- The delete request `DELETE /admin-react/api/v1/library/book/<pk>/`
  returns `204`.
- After step 9, the list view no longer contains the row.

### Negative variants

- **N3a — server validation fails on save.** Submit with a
  duplicate `(title, author)` if the model enforces uniqueness.
  The server returns `400 validation_failed`; field errors are
  rendered inline; the user remains on the create page.
- **N3b — permission lost between create and delete.** Revoke
  `delete_book` after step 6. The delete button is hidden on the
  detail page on the next request (criterion E-2).
- **N3c — confirm-then-cancel.** In step 8, the user clicks the
  dialog's "Cancel". The dialog closes; focus returns to the
  triggering "Delete" button (accessibility A-3).
- **N3d — refresh during the confirm dialog.** Refreshing the page
  closes the dialog. The object is not deleted.

---

## Why exactly three (not five)

A test suite is durable only when it stays small. These three flows
together exercise:

- Auth gate (Flow 1 N1a, N1b, N1c).
- SPA navigation invariants (Flow 1 main).
- Optimistic UI + reconciliation (Flow 2 main + N2c).
- Server-side validation surfacing (Flow 2 N2a).
- Permission loss mid-flow (Flow 2 N2b, Flow 3 N3b).
- Create through admin form (Flow 3 main).
- Destructive action UX (Flow 3 main + N3c, N3d).

Adding more flows in v0.1 dilutes the E2E suite — the marginal flow
catches less than it costs to maintain.

Two **stretch** flows we may add at v0.2:

- **Flow 4** — search + ordering + paginate (once `list_filter` UI
  ships).
- **Flow 5** — inline edit (when inlines ship).

---

## E2E execution notes (for the Architect)

- The suite runs against the test_project's local server on a
  random port.
- Use the `library` example app's fixtures, not bespoke fixtures
  per test — a single seed file keeps the flows realistic.
- Resolution targets: **375 px** (mobile), **1280 px** (desktop).
  Skip the others by default; they live in the visual-regression
  suite.
- Time budget for the suite: **≤ 90 s** wall clock on a
  reference laptop. If we approach that, split flows by tag rather
  than skipping coverage.

---

## Acceptance cross-reference

| Flow             | Criteria                                  |
| ---------------- | ----------------------------------------- |
| 1 main           | P-1, P-4, N-1, N-2, N-3, A-3              |
| 1 negative       | N-5, O-4, O-5, Q-PM-04 (tentative)        |
| 2 main           | D-1, D-2, N-1                             |
| 2 negative       | A-5, D-4, N-4                             |
| 3 main           | E-1, E-2, E-3, D-1                        |
| 3 negative       | A-3 (focus return), data-layer.md §4      |
