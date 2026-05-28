# Product vision

> A Django developer should be able to install one package, mount one
> URL, log in, and feel like they got a modern admin UI for free —
> driven by the same `ModelAdmin` classes they already wrote.

`django-admin-react` is **an adapter**, not a replacement. It extends
`django.contrib.admin` with a responsive single-page UI; it does not
fork its philosophy, its permissions model, or its developer
ergonomics.

This file is the product north star. Every other doc — engineering,
design, roadmap — must be reconcilable with it. When in conflict,
this file wins for product decisions; [`ARCHITECTURE.md`](ARCHITECTURE.md)
wins for technical contracts.

## What's in this repo vs the API repo vs the MCP repo

The project is **three repos** with separate-but-aligned scopes (#544):

- **`django-admin-rest-api`** — the JSON REST API for the Django admin
  ([PyPI](https://pypi.org/project/django-admin-rest-api/) ·
  [GitHub](https://github.com/MartinCastroAlvarez/django-admin-api)).
  The wire surface, the permission gates, the serializer denylist, the
  contract document. **The API repo owns the API.**
- **`django-admin-react`** *(this repo)* — the **React SPA**
  super-layer on top of that API. Frontend, build pipeline, pre-built
  assets, SPA mount, PWA, screenshots. This product vision is about the
  **user-facing UX**, not the wire surface — for anything about wire
  shapes, look in the API repo.
- **[`django-admin-mcp-api`](https://pypi.org/project/django-admin-mcp-api/)**
  ([`MartinCastroAlvarez/django-admin-mcp`](https://github.com/MartinCastroAlvarez/django-admin-mcp))
  — a wire-protocol-only MCP adapter over `django-admin-rest-api`.
  Lets agents reach the same `ModelAdmin`-driven REST surface, no new
  functionality / permissions / validation. Different protocol, same
  source of truth.

If you're a Django developer reading this, you don't need to think about
the split: `pip install django-admin-react` brings in **both** sibling
packages (`django-admin-rest-api` *and* `django-admin-mcp-api`) as
dependencies, and a couple of `INSTALLED_APPS` lines + one URL include
give you the SPA — the MCP server is opt-in on top of the same wire.

---

## 1. Who this is for

The target user is **a Django developer who builds Django apps and
uses `django.contrib.admin` daily**. Concretely:

- They have written at least one `ModelAdmin` subclass.
- They are comfortable in `settings.py` and `urls.py`.
- They are **not** comfortable maintaining a React app.
- They want the admin to look and feel modern — but not at the cost
  of having to learn a new mental model, a new permissions system,
  or a new templating language.

We are **not** primarily building for:

- React engineers who want to rebuild an admin from scratch (use a
  headless CMS or a real SPA framework).
- Designers who need pixel-perfect, brand-bespoke admin UIs (we ship
  a defensible default; full re-skin is "fork the bundle").
- Non-Django backends (this is a Django package; nothing here is
  generic).

## 2. What success looks like

A Django dev going from "I have a Django project" to "I have a modern
admin" should be:

1. **Install** — `pip install django-admin-react`.
2. **Wire** — add to `INSTALLED_APPS`, include the URLs at their
   chosen mount point.
3. **Run** — `manage.py runserver`, log in with their existing staff
   credentials.
4. **Done** — see all their `ModelAdmin`-registered models, in a
   responsive React UI, behaving exactly like the HTML admin would
   have.

**Five minutes, ideally fewer.** Anything in this path that takes
longer is a P0 onboarding bug.

## 3. The five principles

1. **`ModelAdmin` is the only source of truth.** If a behaviour
   exists in the HTML admin, it exists here, driven by the same
   methods (`get_queryset`, `has_*_permission`, `get_form`, …).
   If it does not exist in the HTML admin, we do not invent it.
2. **No React knowledge required for Django devs.** Every customer
   surface — list columns, fields, permissions, filters — is driven
   from server-side Python. Editing a `ModelAdmin` is the entire
   extension API in v1.
3. **Plug-and-play beats configurability.** Sensible defaults
   everywhere. The only required configuration is `INSTALLED_APPS` +
   `include("django_admin_react.urls")`. A single optional dict
   covers the long tail.
4. **The product feels Django-native.** We borrow the admin's
   vocabulary (`app_label`, `model_name`, "object", staff users,
   `is_superuser`), its URL shapes, and its login flow. A Django
   user should never feel they need to learn a new mental model.
5. **Boring beats clever.** Stable, accessible, predictable UI.
   Linear/Notion/GitHub feel — not "the most creative admin you've
   ever seen". Surprises hurt productivity.

## 4. Anti-goals (we will **not** build)

- A separate user / permission model.
- A custom template engine.
- A "page builder" or "form builder" in the UI.
- A React-side plugin API in v1. (Revisit only after community pull.)
- Server-rendered HTML pages — the SPA is the only renderer.
- A new theming language. Theming is Tailwind CSS variables and an
  optional config extension. Full config replacement = "fork your
  bundle".
- A "Django Admin replacement" that hides the HTML admin. Both stay
  available; the consumer chooses which to mount, where.

## 5. Decision filters (use before saying "yes")

Before adding a feature, every contributor should be able to answer
"yes" to **all** of these:

- Does a Django dev expect this to behave the way I'm proposing?
- Can this be inferred automatically from the consumer's `ModelAdmin`?
- Does it preserve the `ModelAdmin` mental model?
- Does it work without requiring the consumer to write JavaScript?
- Does the install/onboarding experience get **simpler**, or at
  least not harder?
- Is the resulting UI legible, accessible, and responsive on the
  smallest target viewport (375 px wide)?

If any answer is "no", the default response is **no** — re-scope or
push to a later milestone.

## 6. Positioning vs related projects

| Project                       | Approach                          | When to pick it instead                         |
| ----------------------------- | --------------------------------- | ----------------------------------------------- |
| `django.contrib.admin`        | Server-rendered, complete         | You like the HTML admin and don't need SPA      |
| `django-jazzmin`, `django-unfold` | CSS reskin of the HTML admin  | You want a new look without changing the model  |
| Wagtail                       | Full CMS                          | You're building a content-heavy site            |
| Headless CMS (Strapi, etc.)   | Admin + your own backend          | You're not Django-first                         |
| **`django-admin-react`**      | Same `ModelAdmin`, new SPA UI     | You want SPA feel without writing React         |

The competitive premise is "you don't have to give up Django Admin to
get a modern admin." If a user has to choose between extensibility
and modernity, we have lost.

## 7. Quality bar (non-negotiable)

A v1 release must, at minimum, satisfy:

- **Install path**: ≤ 5 commands, ≤ 5 minutes, on a clean Python +
  Django 5 environment.
- **Lighthouse-equivalent**: First Contentful Paint < 1.5 s on cached
  load; LCP < 2.5 s on cold load (target hardware: M-class laptop on
  a 10 Mbps connection).
- **Accessibility**: WCAG 2.1 AA on every shipped page (see
  [`docs/ux/accessibility.md`](docs/ux/accessibility.md)).
- **Responsive**: usable down to 375 px width; full feature parity at
  768 px+. No horizontal page scroll.
- **Keyboard**: every interactive element reachable + actionable
  without a mouse.
- **Dark mode**: ships in v1 (Linear/GitHub-style toggle following
  `prefers-color-scheme` by default).
- **Security**: see [`SECURITY.md`](SECURITY.md). Non-negotiable;
  product never trades correctness for polish.

## 8. What "modern feel" means here

Not just "looks new". Specifically:

- Single-page navigation (no full reload between list / detail).
- Instant first paint (cached payload via `@dar/data` —
  [`docs/data-layer.md`](docs/data-layer.md)).
- Optimistic updates on field edits (debounced flush; rollback on
  rejection).
- Predictable focus management on route change.
- Subtle motion (≤ 150 ms); respects `prefers-reduced-motion`.
- Skeletons over spinners.
- Keyboard shortcuts that feel like Linear / GitHub (`/` to search,
  `cmd+k` for command palette — v1.x).
- No flashes of unstyled content. No layout shift.

## 9. Cross-references

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — what the system **is**.
- [Project board](https://github.com/users/MartinCastroAlvarez/projects/3)
  — what we **build** next, in priority/phase order.
- [Open Issues](https://github.com/MartinCastroAlvarez/django-admin-react/issues)
  — what users will **get** (each issue carries the acceptance signal).
- [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) — how it **looks**.
- [`ONBOARDING.md`](ONBOARDING.md) — how a dev **starts**.
- [`docs/ux/`](docs/ux/) — the UX rules in detail.
