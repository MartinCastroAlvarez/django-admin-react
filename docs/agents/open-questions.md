# Open questions

Questions awaiting a decision. When answered, move the resolved summary
to [`decisions.md`](decisions.md).

## Format

```
## <topic> — opened YYYY-MM-DD

Context: one or two sentences on why this matters.

Options considered:
- A: <one-liner>
- B: <one-liner>

Tentative direction (if any): …

— <agent-id-or-author>
```

---

## [SEC] QSEC-2026-05-25-01 — Rate limiting for the API

Context: A logged-in staff user can hit `GET /api/v1/...` at any rate
Django allows. For a popular consumer, an abusive insider or a
compromised session could iterate every object.

Options:

- A: Document a recommended `django-ratelimit` integration; don't
  bundle a runtime dependency.
- B: Add an opt-in soft limit via `DJANGO_ADMIN_REACT["RATE_LIMIT"]`
  using Django's cache framework.
- C: Defer entirely to the consumer (current behavior).

Tentative direction: **A**. Pending Architect review.
— `claude-security-opus47-1`

---

## [SEC] QSEC-2026-05-25-02 — Audit logging via `LogEntry`

Context: Should writes generate an audit-log entry? Django admin's
`LogEntry` already records changes from the HTML admin.

Options:

- A: Reuse `django.contrib.admin.models.LogEntry`; emit entries
  through `construct_change_message`.
- B: Define our own log model — rejected (parallel system).
- C: No logging from the package; rely on consumer signals.

Tentative direction: **A**. To be codified in `SECURITY.md` once
write endpoints land.
— `claude-security-opus47-1`

---

## [SEC] QSEC-2026-05-25-03 — CSP defaults for the SPA shell

Context: The SPA shell renders `index.html` from a Django template.
Should the package ship a recommended Content-Security-Policy?

Tentative direction: ship a sample CSP middleware snippet in
`docs/installation.md` (consumer-applied), not in package
middleware. — `claude-security-opus47-1`

---

## [SEC] QSEC-2026-05-25-04 — Subresource Integrity on the bundle

Context: Vite hashes the bundle filename, but a CDN could still
substitute a malicious bundle.

Tentative direction: compute and inject SRI hashes during
`scripts/build.sh` once PR #6 lands. — `claude-security-opus47-1`

---

## [SEC] QSEC-2026-05-25-05 — Session expiration / idle timeout

Context: Should the package nudge consumers to set
`SESSION_COOKIE_AGE` more conservatively for staff sessions?

Tentative direction: documentation-only recommendation in
`SECURITY.md` §"Recommended consumer settings". —
`claude-security-opus47-1`

---

## Q-2026-05-25-01 — Should we hard-depend on `djangorestframework`?

Context: the v1 API does CRUD over JSON. DRF would give us serializers,
exception handling, content negotiation, throttling, and a familiar idiom
for consumers. But DRF is a heavy dependency, has its own permission
system that we explicitly *don't* want to use, and adds a security
surface area.

Options:

- **A.** Build on Django's stock class-based views; write small,
  conservative serialization helpers ourselves. Smaller surface. More
  custom code.
- **B.** Depend on DRF; reuse its serializers and views. Bigger
  dependency. Risk of agents drifting to "use DRF permissions" out of
  habit.

Tentative direction: **A.** Reasons: smaller install surface, fewer
"don't use this DRF feature" rules to enforce. Recorded as the working
assumption in `PLAN.md` §4. Revisit if hand-rolled serialization becomes
maintenance burden.

— claude-foundation-opus47

---

## Q-2026-05-25-02 — How should we handle a custom `AdminSite`?

Context: a consumer may register a subclass of `AdminSite` with
overridden `has_permission`, a different `_registry`, or a custom URL
namespace. v1 supports one admin site via
`DJANGO_ADMIN_REACT["ADMIN_SITE"]` dotted path.

Options:

- **A.** Single-site v1. Multi-site is a v1.x feature. Documented in
  `ARCHITECTURE.md` §4.6.
- **B.** Multi-site in v1 with a list of dotted paths.

Tentative direction: **A.** Smaller v1; clear path to B later.

— claude-foundation-opus47

---

## Q-2026-05-25-03 — Frontend test runner

Context: PR #6 introduces the frontend monorepo. We need to pick a test
runner that plays well with Vite, React Query, and Tailwind.

Options:

- **A.** Vitest + Testing Library.
- **B.** Jest + Testing Library.

Tentative direction: **A** (Vitest), because Vite is already the build
tool — no separate transform pipeline. Pending confirmation in PR #6.

— claude-foundation-opus47

---

## Q-2026-05-25-04 — Bundle delivery: WhiteNoise vs Django staticfiles

Context: the React bundle ships in
`django_admin_react/static/admin_react/`. Consumers serve static files
in different ways (collectstatic + nginx, WhiteNoise, etc.).

Options:

- **A.** Document that the bundle is a normal `static/` directory.
  Consumers wire it in like any other static. No new dependency.
- **B.** Ship with WhiteNoise as a recommended add-on.

Tentative direction: **A** for v1. No new runtime dep.

— claude-foundation-opus47

---

## Q-2026-05-25-05 — Are M2M fields read-only or hidden in v1?

Context: the spec defers M2M editing. The API doc currently exposes M2M
as `type: "unsupported"` (read-only label, no edit control).

Options:

- **A.** Show as read-only "unsupported" field with a clear label.
  Surfaces presence without breaking editing.
- **B.** Hide entirely.

Tentative direction: **A.** Hiding silently is worse UX than honestly
saying "this isn't editable here yet."

— claude-foundation-opus47

---

> Add new questions above this line, newest on top.
