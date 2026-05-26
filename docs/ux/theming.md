# Theme + dark mode

The SPA ships with a built-in light/dark theme toggle, persisted
across visits and resilient to first-paint flash. Tracked under
[issue #84](https://github.com/MartinCastroAlvarez/django-admin-react/issues/84).

Maps to [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2.8 V-5 (dark mode
is a designed counterpart, not an inverted CSS afterthought).

---

## 1. Three theme options

The user-menu carries a `Theme` control with three values:

| Value         | Behaviour                                                                      |
| ------------- | ------------------------------------------------------------------------------ |
| `Light`       | Apply the light token set. Persists across visits regardless of OS preference. |
| `Dark`        | Apply the dark token set. Persists across visits regardless of OS preference.  |
| `Match system` | Follow the OS preference at each page load; re-evaluate on `prefers-color-scheme` changes. **Default for new visitors.** |

The selection persists to `localStorage["dar:v1:theme"]` (values:
`"light"`, `"dark"`, `"system"`).

---

## 2. No first-paint flash

The most common dark-mode bug is a flash of light theme before the
JS hydrates and sets `data-theme="dark"`. We solve it server-side.

### 2.1 The handshake

- The Django view that serves the SPA HTML (`SpaIndexView`) inspects
  the request's **`Sec-CH-Prefers-Color-Scheme`** client hint
  (a W3C standard sent by modern Chromium when the consumer
  requests it via `Accept-CH`).
- The view also reads the **`dar_theme`** cookie (set by the SPA
  when the user picks Light or Dark explicitly).
- Resolution order (highest priority first):
  1. `dar_theme` cookie value (`"light"` or `"dark"`).
  2. `Sec-CH-Prefers-Color-Scheme` (`"light"` / `"dark"` / `"no-preference"`).
  3. Default to `"light"`.
- The resolved theme is rendered into the response as
  `<html data-theme="dark">` (or `"light"`) **before** any JS runs.

### 2.2 Why this (not an inline `<script>`)

`<script>` inlined into the HTML would set the attribute pre-hydrate
but would also need `'unsafe-inline'` in the CSP `script-src`
directive, violating [`SECURITY.md`](../../SECURITY.md) §4.11 (CSP
posture). Server-side resolution preserves `script-src 'self'`.

The trade-off: visitors on browsers without the client hint
(notably Safari) get the light default on first paint, then the
SPA hydrates and re-applies their persisted preference. The flash
window is one repaint; acceptable for v1.

### 2.3 Cookie shape

```
dar_theme=light; Path=/; SameSite=Lax; Secure; Max-Age=31536000
```

- `HttpOnly` is **not** set — the SPA reads the cookie to confirm
  the server-side resolution matched. This is the only `dar_*`
  cookie the package writes; not a session-shaped value, no PII.
- Lifetime one year. Cleared via the user-menu "Reset to system".
- `Secure` is set **only when `request.is_secure()` returns True**
  (i.e. HTTPS). On plain-HTTP dev environments the flag is omitted
  so the cookie still round-trips. The cookie's role is theme
  persistence only; absence of `Secure` on plain HTTP does not
  introduce a new auth surface — the theme value is not
  session-derived and carries no PII. (Security-lane note added
  2026-05-26 as part of the PR #102 follow-up.)

---

## 3. Token mechanics

The SPA's design tokens live in [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md)
§3 as CSS variables. Dark mode flips the variables, not the
stylesheet:

```css
:root { --dar-bg: #ffffff; --dar-fg: #0a0a0a; ... }
[data-theme="dark"] { --dar-bg: #0a0a0a; --dar-fg: #ededed; ... }
```

No second stylesheet, no `[class~="dark"]` switch. Component code
doesn't know which theme is active — it consumes `var(--dar-*)`.

---

## 4. Dark mode is **designed**, not inverted

Per V-5: every screen has a dark counterpart with **adjusted**
colours, not simply inverted. Specific rules:

- Errors, warnings, and success states use **muted** dark-mode
  variants of their light tokens — full-saturation red on a dark
  background reads as a screaming alarm.
- Code / monospace surfaces use the consumer's preferred syntax
  theme via the same CSS-var layer; the default in dark is
  `bg-zinc-900` + `text-zinc-100`, not "inverted light".
- Charts and data viz (v1.x) keep categorical hues but reduce
  lightness by ~15 %.
- Borders are **not** inverted to white — they shift to
  `oklch(0.3 ...)` so they read as separators, not lines.

---

## 5. Acceptance signals

Each row will be lifted into `ACCEPTANCE.md` §2.8 when this lands.

| Row | Criterion                                                                                                |
| --- | -------------------------------------------------------------------------------------------------------- |
| V-6 | The SPA exposes a `Theme` control (Light / Dark / Match system) in the user menu. Choice persists across reloads. |
| V-7 | A fresh visit with `prefers-color-scheme: dark` renders the dark theme on the **first paint** — no flash from light. |
| V-8 | Toggling `Theme` while on any SPA page swaps tokens **in place** without a route change, scroll reset, or unmount. |

---

## 6. What the package **never** does

- Modify `<html class>` (only `data-theme`) — leaves the class
  attribute available for consumer-side CSS hooks.
- Ship a `?theme=` query parameter — the cookie + client hint is
  the contract; query-string control would invite open-redirect
  permutations.
- Persist the theme server-side per user. Per-browser localStorage
  is the v1 contract; per-user theme is out of scope.
- Detect the OS preference via JavaScript `matchMedia` *for the
  initial paint* — the client hint is the only initial-paint
  signal. `matchMedia` is consulted only for live updates while
  the SPA is mounted with `Theme = "Match system"`.

---

## 7. Cross-references

- Issue [#84](https://github.com/MartinCastroAlvarez/django-admin-react/issues/84) — tracking.
- [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) §3 — token list.
- [`SECURITY.md`](../../SECURITY.md) §4.11 — CSP `script-src 'self'`
  invariant the server-side handshake preserves.
- [`pwa.md`](pwa.md) — the PWA manifest's `theme_color` /
  `background_color` use the same server-side resolution.
- [`docs/screenshots/README.md`](../screenshots/README.md) — every
  screen requires a light + dark counterpart per the inventory.
