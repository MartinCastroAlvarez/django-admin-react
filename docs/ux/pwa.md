# PWA: installability + offline shell

The SPA is **installable** on Android and on desktop browsers that
implement the install prompt. Once installed, the app loads from
the service-worker-cached shell — first paint is near-instant on
subsequent visits, and read paths keep working when the network
is flaky. Tracked under
[issue #86](https://github.com/MartinCastroAlvarez/django-admin-react/issues/86).

Maps to a new `ACCEPTANCE.md` §2.13 block (criteria I-1..I-6,
drafted in §6 below; lifted into `ACCEPTANCE.md` when this lands).

---

## 1. Manifest

The package serves a **single Django view at `<mount>/web.manifest`**,
unauthenticated (matches the install-prompt UX — the install dialog
needs the manifest before login). The view's response is computed
at request time so `start_url` / `scope` / `name` reflect the
consumer-chosen mount + `AdminSite.site_header`.

Theme is server-resolved from `Sec-CH-Prefers-Color-Scheme`,
pairing with the [`theming.md`](theming.md) §2 client-hint path —
no `?theme=` query, no static dual-variant file.

### Fields

| Field             | Value                                                                          |
| ----------------- | ------------------------------------------------------------------------------ |
| `name`            | `"<verbose name of the Django project> admin"` — defaults to `AdminSite.site_header`. |
| `short_name`      | `"Admin"` — overridable via `DJANGO_ADMIN_REACT["PWA_SHORT_NAME"]`.            |
| `start_url`       | The SPA mount URL resolved at request time.                                    |
| `scope`           | Same as `start_url`. The SW never claims pages outside the mount.              |
| `display`         | `"standalone"` — full-app feel on Android; falls back to `"minimal-ui"`.       |
| `orientation`     | `"any"` — admin work happens in both orientations.                              |
| `background_color`| Resolved theme's `--dar-bg` value (from the client hint).                       |
| `theme_color`     | Resolved theme's `--dar-accent` value.                                          |
| `icons`           | `192×192` + `512×512`, plus a `512×512` maskable variant.                       |

Default icon set ships in `django_admin_react/static/dar/icons/`.
Consumers override via `DJANGO_ADMIN_REACT["PWA_ICONS"]` (list of
`{src, sizes, type, purpose}` dicts).

If the consumer never sets any PWA setting, the defaults are sane
and the manifest works.

---

## 2. Service worker

Hand-rolled SW at `<mount>/sw.js` — **not** `vite-plugin-pwa`.
Rationale: `vite-plugin-pwa` pulls Workbox (~30 KiB) and most of
its features we don't use. Owning the SW JS ourselves keeps it
auditable and the Tier-5 dependency surface small (no new npm
dep). The SW + manifest emission piggybacks on the existing
`scripts/build.sh` static-copy step.

The SW registers automatically when the page loads under the SPA
mount; scope is the same `start_url`. The package serves the JS
with `Service-Worker-Allowed: <mount>` header.

### 2.1 Cache policy

| Asset class                              | Strategy                                                | Reasoning                                              |
| ---------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| SPA shell (`index.html`, JS, CSS)        | Stale-while-revalidate, versioned cache.                | Hash-named bundles; near-instant repeat-load.          |
| Static icons / fonts / images            | Cache-first, immutable cache (1-year TTL).              | Hashed filenames, safe to cache forever.               |
| Manifest                                 | Network-first (cheap; theme may change).                | Re-fetched on each visit.                              |
| `/api/v1/registry/`                      | Network-first, fall back to last good cache.            | Permissions can change; prefer fresh, offline OK.      |
| `/api/v1/<app>/<model>/`                 | Network-first, last-good cache.                         | Same reason.                                           |
| `/api/v1/<app>/<model>/<pk>/`            | Network-first, last-good cache **per-pk**.              | Same reason.                                           |
| Action invocations / writes              | **No SW caching, no replay.** Must hit the network.     | Mutation safety. See §4.                               |
| Anything outside the SPA mount           | **Pass through.** SW does not intercept.                | Don't surprise other Django views.                     |

The SW respects `Cache-Control: no-store` from the server and
skips caching that response — preserves the existing 200/401/403
`no-store` policy from [`SECURITY.md`](../../SECURITY.md) §4.7.

### 2.2 Scope guarantee

The SW does **not** claim any URL outside the SPA mount. A
consumer who serves other Django views (admin login, project
pages) at sibling paths gets zero interference.

---

## 3. Install prompt UX

### 3.1 Native prompt path

- Browser fires `beforeinstallprompt`. The SPA captures the event,
  stores it, and renders the **Install** affordance (§3.2).
- User clicks the affordance → SPA calls `prompt()` on the captured
  event. Browser shows its native dialog.
- After accept / dismiss, log to `localStorage["dar:v1:install_state"]`
  (`"accepted"`, `"dismissed"`). If `"dismissed"`, hide the
  affordance for **14 days**.

### 3.2 The affordance

- **User menu (top-right)** — menu item labelled "Install this
  admin" with the Lucide `Download` icon. Visible only when a
  `beforeinstallprompt` event is captured.
- **User-menu drawer (mobile)** — same item, third from the top
  (above logout).
- **Already-installed visit** — affordance hidden; the
  `appinstalled` event sets a flag.

### 3.3 What we never do

- Auto-show a modal asking to install. The browser's native prompt
  is the only modal. Our affordance is a button.
- Show the affordance every visit if the user dismissed. Respect
  the 14-day cooldown.
- Show the affordance on iOS Safari (no `beforeinstallprompt`);
  iOS users see a one-line tip in the user menu pointing at
  "Add to Home Screen" in Safari's share sheet.

---

## 4. Offline behaviour

- **Read paths** keep working from the SW cache when offline.
  Skeleton loading from [`states.md`](states.md) §1 fires only on
  first-ever visit to a model; subsequent visits hydrate from cache.
- **Write paths** show a sticky banner: *"You're offline. Changes
  will save when you reconnect."* Mutations enter the `@dar/data`
  debounced queue but do **not** flush; they flush on the next
  `online` event.
- **Failed writes on reconnect** — the existing rollback flow
  ([`states.md`](states.md) §4) fires.
- **Login required, but offline** — show the existing 403
  `session_expired` toast with "Reconnect to sign in"; reads keep
  working if cache-hits.

---

## 5. Cache purge on logout

When the user logs out, the SPA must `caches.delete(...)` for the
SPA caches so cached API payloads don't outlive the session.

The package's `<mount>/logout/` redirect path triggers an SPA-side
hook before navigating away: iterate `caches.keys()`, filter for
`dar:v1:*`, delete. No-op when there's nothing cached.

This is **explicit in the contract** because the alternative
(rely on session-cookie expiry) leaks read-cached payloads to a
later user of the same browser. Defense-in-depth atop session
expiry, not a replacement for it.

---

## 6. Acceptance signals (proposed `ACCEPTANCE.md` §2.13)

| Row  | Criterion                                                                                                |
| ---- | -------------------------------------------------------------------------------------------------------- |
| I-1  | Visiting the SPA on Android Chrome over HTTPS fires the install prompt within the browser's heuristics.  |
| I-2  | The installed app launches in `display: standalone` mode and serves a cached shell on cold start.        |
| I-3  | Read paths (registry, list, detail) work for ≥5 minutes after killing the network.                        |
| I-4  | Write attempts during offline render the "Changes will save when you reconnect" banner and queue mutations. |
| I-5  | The Install affordance respects a 14-day cooldown after dismissal and disappears post-install.            |
| I-6  | Logout fires `caches.delete(dar:v1:*)`; a follow-up cold load against the same browser shows fresh data. |

---

## 7. Security posture (asks for Security lane)

- Confirm the SW cache for API responses doesn't retain payloads
  beyond logout — the cache purge in §5 must be testable
  end-to-end.
- Confirm the `Cache-Control: no-store` honour rule is testable.
- Confirm CSP additions: `worker-src 'self'` required; `connect-src
  'self'` unchanged.

---

## 8. Cross-references

- Issue [#86](https://github.com/MartinCastroAlvarez/django-admin-react/issues/86) — tracking.
- [`theming.md`](theming.md) — manifest theme colours via the same
  `Sec-CH-Prefers-Color-Scheme` handshake.
- [`states.md`](states.md) §3.5 — session-expiry flow extended with
  the offline banner copy.
- [`responsive.md`](responsive.md) §9 — mobile patterns the
  installed-app experience preserves.
- [`SECURITY.md`](../../SECURITY.md) §4.7 — `Cache-Control`
  policy the SW honours.
