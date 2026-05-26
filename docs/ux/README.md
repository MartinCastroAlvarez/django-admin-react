# docs/ux/

UX rules for `django-admin-react`. Owned by the PM/UX role (see
[`docs/agents/product-manager/AGENT.md`](../../docs/agents/product-manager/AGENT.md)).

These docs are the long-form companion to [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md)
and [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2. Every rule here is
testable, every claim cross-references an acceptance criterion.

## Index

| File                                       | Topic                                                |
| ------------------------------------------ | ---------------------------------------------------- |
| [`principles.md`](principles.md)           | UX laws and how they apply to a Django admin.        |
| [`states.md`](states.md)                   | Loading / empty / error / optimistic spec.           |
| [`navigation.md`](navigation.md)           | SPA navigation and the URL contract.                 |
| [`accessibility.md`](accessibility.md)     | WCAG 2.1 AA checklist with examples.                 |
| [`responsive.md`](responsive.md)           | Breakpoints, table → card, touch targets, mobile patterns (FAB / bottom-sheet / swipe). |
| [`theming.md`](theming.md)                 | Light / dark theme contract, no-flash server-side resolution. |
| [`pwa.md`](pwa.md)                         | Installability, service worker, offline shell, cache-on-logout. |
| [`extensibility.md`](extensibility.md)     | Plug-and-play vs extensibility contract (X-1..X-7).  |
| [`primary-flows.md`](primary-flows.md)     | End-to-end flows tied to acceptance criteria.        |

## Conventions

- **One rule per heading.** Headings are stable; the body may grow.
- **Cross-references are mandatory.** Any rule that maps to an
  acceptance criterion must cite the criterion id (e.g., "R-2").
- **No prose-only rules.** Every rule must have either a measurable
  threshold or a list of examples.

## Related

- [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) — the why.
- [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md) — the tokens and
  primitives.
- [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §2 — what we measure.
