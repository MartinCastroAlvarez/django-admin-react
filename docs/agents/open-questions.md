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

## [SEC] QSEC-2026-05-25-03 — CSP defaults for the SPA shell → RESOLVED

Context: The SPA shell renders `index.html` from a Django template.
Should the package ship a recommended Content-Security-Policy?

**Resolved (2026-05-27):** consumer-applied recommendation, **not** package
middleware (the package never imposes headers on the consumer's project).
The concrete policy now lives in [`SECURITY.md`](../../SECURITY.md) §9
("Content-Security-Policy") — grounded in the shell's actual asset graph
(same-origin bundle, no inline `<script>`, so `script-src 'self'` holds),
with Report-Only rollout + cross-origin-storage caveats. Landed in
`SECURITY.md` rather than the never-created `docs/installation.md`
(the old "PR #6" deferral was stale). — `claude-security-opus47`

---

## [SEC] QSEC-2026-05-25-04 — Subresource Integrity on the bundle

Context: Vite hashes the bundle filename, but a CDN could still
substitute a malicious bundle.

Tentative direction: compute and inject SRI hashes during
`scripts/build.sh` once PR #6 lands. — `claude-security-opus47-1`

---

## Q-2026-05-25-03 — Frontend test runner

Context: PR #6 introduces the frontend monorepo. We need to pick a test
runner that plays well with Vite, React Query, and Tailwind.

Options:

- **A.** Vitest + Testing Library.
- **B.** Jest + Testing Library.

Tentative direction: **A** (Vitest), because Vite is already the build
tool — no separate transform pipeline. **Still pending — frontend
packages do not yet declare a test runner in `package.json`. The first
frontend test PR confirms the direction.**

— claude-foundation-opus47

---

> Add new questions above this line, newest on top.

> **Resolved 2026-05-26** — Q-2026-05-25-01 (DRF: A — no DRF dep
> confirmed in `pyproject.toml`), Q-2026-05-25-02 (single AdminSite:
> A — `conf.py` `ADMIN_SITE` is a single dotted-path string),
> Q-2026-05-25-04 (bundle delivery: A — no WhiteNoise dep),
> Q-2026-05-25-05 (M2M visibility: obsoleted by [PR #107](https://github.com/MartinCastroAlvarez/django-admin-react/pull/107) which
> shipped M2M read+write — the "unsupported stub" framing no longer
> applies). Moved to [`decisions.md`](decisions.md).

---

## Cross-role questions

When a question spans multiple roles (PM × Architect, PM × Security,
etc.) record it here, marked with the involved roles.

## Q-2026-05-25-CX-01 — Should `mount` in `/api/v1/registry/` be **absolute** or **request-derived**?

Roles involved: PM / Architect.
Owner (asking): PM/UX (`claude-pm-ux-opus47`).
Context: [`PRODUCT_VISION.md`](../../PRODUCT_VISION.md) requires the
package to work at any URL mount the consumer chooses. The registry
endpoint currently returns `mount` derived from `request.path`
(`docs/api-contract.md` §2). If the consumer is behind a reverse
proxy that strips the prefix, this could break SPA link generation.

Options:

- **A.** Keep request-derived `mount`. Document that consumers
  behind path-stripping proxies must restore the prefix
  (`SCRIPT_NAME` / `FORCE_SCRIPT_NAME`).
- **B.** Add an optional `DJANGO_ADMIN_REACT["MOUNT_OVERRIDE"]`
  setting that pins the value.

Tentative direction (PM): **A** for v1; document in
`ONBOARDING.md`. Adding another settings key violates the
"minimum configuration" principle. Revisit if a real consumer hits
this.

— `claude-pm-ux-opus47`

**Resolved 2026-05-26 (A — request-derived).** `django_admin_react/views.py:109` reconstructs the mount from `request.path` and embeds it in the SPA template via the `dar-mount` meta tag; PR #120 hardened the SPA-side `detectMount()` to honour it. Consumers behind path-stripping proxies set `FORCE_SCRIPT_NAME` per the standard Django pattern. Moved to [`decisions.md`](decisions.md).

---

## Q: Datetime display timezone — viewer-local vs `settings.TIME_ZONE`? (#413)

Roles involved: Architect / PM.
Owner (asking): `claude` (this session).
Context: #413 asks that datetimes stop rendering as raw UTC ISO. The
SPA now formats `datetime`/`date`/`time` columns via the browser's
`toLocaleString` (PR for #413), i.e. in the **viewer's local
timezone**. The backend emits offset-aware ISO under `USE_TZ=True`, so
the displayed instant is correct; only the *zone* differs from the HTML
admin, which renders in `settings.TIME_ZONE`.

Options:

- **A (shipped).** Viewer-local zone. SPA-idiomatic, zero config,
  correct instant. Differs from the HTML admin only when the operator's
  browser zone ≠ `settings.TIME_ZONE` (uncommon — operators are usually
  in the configured zone).
- **B.** Honour `settings.TIME_ZONE` for strict HTML-admin parity:
  backend `timezone.localtime()` + the SPA formats the ISO *components*
  without re-converting the instant. More code; pins display to the
  server's configured zone regardless of where the operator sits.

Tentative direction: **A** for v1 (simpler, idiomatic). Revisit to **B**
if a consumer reports a zone mismatch against the HTML admin.

— `claude`
