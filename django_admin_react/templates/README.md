# django_admin_react/templates/

Server-rendered templates the package ships. Kept deliberately minimal —
the UI is the React SPA; these templates only cover what *must* be
server-rendered.

What lives here:

- [`admin_react/`](admin_react/) — the package's own templates:
  - the SPA shell (`index.html`-style entry that boots the React app and
    carries the CSRF cookie + the `<meta name="dar-mount">` tag), and
  - `sw.js` — the hand-rolled service worker served at the mount root
    (scope-bounded, honours `no-store`, cache-purge on logout). See
    `django_admin_react/pwa.py` and `docs/threat-model.md` §4.16.

What does **not** belong here:

- React components or any SPA source — those live under
  `frontend/` and ship as the pre-built bundle in
  `django_admin_react/static/`.
- Per-model or example-specific templates — the package is
  metadata-driven and never hard-codes a consumer's models.

Pointers: [`../views.py`](../views.py) (serves the shell),
[`../pwa.py`](../pwa.py) (manifest + service worker),
[`../../docs/threat-model.md`](../../docs/threat-model.md) (SPA shell + PWA
threat analysis).
