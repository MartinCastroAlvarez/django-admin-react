# SPA navigation + URL contract

The SPA must feel like a single application, but URLs are part of
the UX. A bookmarked URL is the user's most reliable way to come
back to where they were.

Maps to [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.7.

---

## 1. URL contract

| Screen                | URL shape                                                |
| --------------------- | -------------------------------------------------------- |
| Registry              | `<mount>/`                                               |
| List view             | `<mount>/<app_label>/<model_name>/?q=&page=&ordering=`   |
| Detail view           | `<mount>/<app_label>/<model_name>/<pk>/`                 |
| Create view           | `<mount>/<app_label>/<model_name>/add/`                  |
| Delete confirm view   | `<mount>/<app_label>/<model_name>/<pk>/delete/`          |

Rules:

- **The URL is the source of truth** for screen state that should be
  shareable: app, model, pk, search, page, ordering.
- Refreshing any URL must yield the same view.
- Sharing the URL with a colleague must yield (within permissions)
  the same view.
- The mount prefix is whatever the consumer chose; the SPA computes
  links relative to `mount` from the registry response.
- URLs are **lowercase** for app/model segments (matching Django's
  `model_name`).

---

## 2. Navigation rules

### 2.1 No full page reloads between primary screens

Going from registry → list → detail → edit → list never reloads
the document. Only the JSON payload changes.

Maps to N-1.

### 2.2 Back / forward / refresh preserve state

- The browser back button returns to the previous URL **and**
  scroll position.
- `Cmd+Shift+T` (reopen tab) restores the most recent URL.
- Refresh re-fetches the same payload.

Maps to N-2.

### 2.3 Deep links survive permission loss

If a user follows a bookmarked URL to a model they no longer have
view permission for, the SPA shows the `403 forbidden` EmptyState,
not a stack trace or a blank screen.

Maps to N-4.

### 2.4 Session expiry redirects through Django

When the API returns `401` / `403` because the session lapsed:

- The current screen state is preserved in `sessionStorage` under
  `dar:v1:resume`.
- The SPA redirects to `LOGIN_URL` with `?next=<current_url>`.
- After successful login Django redirects back to the URL; the SPA
  rehydrates from `dar:v1:resume` if the URL matches.

Maps to N-5.

---

## 3. Focus management

When the URL changes:

1. Move focus to the first heading on the new screen (`<h1>`).
2. Set `document.title` to "<app> · <model_name_plural> — Django Admin".
3. Announce the change via the polite live region so screen readers
   know the page changed.

When a modal opens:

1. Trap focus inside the modal.
2. Restore focus to the trigger element on close.

Maps to acceptance §2.5 A-3, A-4.

---

## 4. Breadcrumb

Every screen shows a breadcrumb:

`<App verbose_name> / <Model verbose_name_plural> / <object label>`

- Each segment is a real link (no decorative "you are here").
- The breadcrumb is **horizontally scrollable** on narrow viewports
  (instead of wrapping or truncating).
- On the registry page, the breadcrumb is omitted (one-level shell).

---

## 5. Keyboard shortcuts

v1 ships these only:

| Key      | Action                                          |
| -------- | ----------------------------------------------- |
| `Tab`    | Focus the next interactive element.             |
| `Esc`    | Dismiss modal / drawer / blur input.            |
| `Enter`  | Submit the focused form / activate the focused button. |
| `?`      | Show "shortcuts help" overlay (v1.1).           |
| `/`      | Focus the list view's search input.             |

Deferred to v1.x / v1.1:

- `Cmd+K` command palette.
- `g` then `l` / `g` then `d` Gmail-style navigation.

Maps to [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) §8; tracked
on the
[Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
under Phase v0.2.

---

## 6. Anti-patterns

- **Hash-fragment routing.** No `#/admin/...`. We use real path
  routing (HTML5 History API).
- **Replacing the URL after a 403.** Keep the URL intact so the user
  can retry once permissions change.
- **Silent route changes** (e.g., redirecting on click without
  user-visible URL change).
- **Anchor scrolling without focus move.** Scroll is for sighted
  users; focus is for everyone.

---

## 7. Acceptance cross-reference

| Behaviour                       | Criterion |
| ------------------------------- | --------- |
| No full reloads                 | N-1       |
| Back/forward preserve scroll    | N-2       |
| URL is source of truth          | N-3       |
| Deep links survive perm loss    | N-4       |
| Session expiry redirect         | N-5       |
| Keyboard reachable              | A-3       |
| Focus moves on route change     | A-3       |
| Mobile breadcrumb scroll        | R-1, R-2  |
