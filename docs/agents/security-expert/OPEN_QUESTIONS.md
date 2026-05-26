# OPEN QUESTIONS — Security & Compliance Lead

Security questions awaiting a decision (mine, the human's, or
another agent's). When answered, move the summary to
[`DECISIONS.md`](DECISIONS.md) and remove from here.

Mirror major ones to `docs/agents/open-questions.md` with the
`[SEC]` tag so non-security agents see them.

---

## QSEC-2026-05-25-01 — Rate limiting for the API

Context: A logged-in staff user can hit `GET /api/v1/...` at any rate
Django allows. For a popular consumer, an abusive insider or a
compromised session could iterate every object in every model.

Options:

- **A.** Document a recommended `django-ratelimit` integration; do
  not bundle a runtime dependency.
- **B.** Add an opt-in soft limit via `DJANGO_ADMIN_REACT["RATE_LIMIT"]`
  using Django's cache framework.
- **C.** Defer entirely to the consumer (current behavior).

Tentative direction: **A** (document, don't bundle). Open until the
Architect agent weighs in.

---

## QSEC-2026-05-25-02 — Audit logging

Context: Should writes generate an audit-log entry the consumer can
observe? Django admin's `LogEntry` already records changes; do we
mirror that, extend it, or leave it alone?

Options:

- **A.** Reuse `django.contrib.admin.models.LogEntry`; emit entries
  through `construct_change_message` like the HTML admin does.
- **B.** Define our own log model — rejected (parallel system).
- **C.** No logging from the package; rely on Django middleware /
  consumer signals.

Tentative direction: **A.** Re-use the admin's `LogEntry` so the
React UI looks the same in the audit timeline as the HTML admin.
Codify this in `SECURITY.md` once the write endpoints land.

---

## QSEC-2026-05-25-03 — CSP defaults

Context: The SPA shell renders `index.html` from a Django template.
Should we ship a recommended Content-Security-Policy header?

Options:

- **A.** Ship a sample CSP middleware snippet in
  `docs/installation.md` (consumer chooses to apply).
- **B.** Apply a strict CSP via the package's own middleware (risky;
  could break existing admin extensions).
- **C.** Stay silent.

Tentative direction: **A.** Stay deferential; document a recommended
CSP that doesn't break the bundle.

---

## QSEC-2026-05-25-04 — Subresource Integrity on the SPA bundle

Context: The SPA bundle is hashed by Vite (e.g.,
`index.<hash>.js`). Should we add `integrity="sha384-..."` to the
`<script>` tag in `index.html` so a CDN can't quietly substitute a
malicious bundle?

Options:

- **A.** Compute and inject SRI hashes at `scripts/build.sh` time.
- **B.** Defer (the package serves the bundle from same-origin
  `staticfiles`, so SRI matters only if the consumer pushes the
  bundle to a CDN).

Tentative direction: **A** is cheap once `scripts/build.sh` is real.
Open until PR #6 lands the build pipeline.

---

## QSEC-2026-05-25-05 — Session expiration / idle timeout

Context: Should the package nudge consumers to set
`SESSION_COOKIE_AGE` more conservatively for staff sessions?

Tentative direction: documentation-only recommendation in
`SECURITY.md` §"Recommended consumer settings" — don't override
the consumer.

---

> New questions above this line, newest on top. Format:
> `## QSEC-YYYY-MM-DD-NN — short title`
