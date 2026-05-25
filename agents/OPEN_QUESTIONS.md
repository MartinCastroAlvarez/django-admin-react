# Cross-role open questions

Shared open questions across PM / Architect / Security roles. When a
question is answered, move the resolved summary to
[`agents/DECISIONS.md`](DECISIONS.md) (or to the relevant role's
`DECISIONS.md` if it is single-owner).

Per-role open questions live in `agents/<role>/OPEN_QUESTIONS.md`.

## Format

```
## Q-<date>-<NN> — <one-line topic>

Roles involved: PM / Architect / Security
Owner (asking): <role>
Context: one or two sentences.
Options:
- A: ...
- B: ...
Tentative direction: ...

— <agent-id>
```

---

## Q-2026-05-25-CX-01 — Should `mount` in `/api/v1/registry/` be **absolute** or **request-derived**?

Roles involved: PM / Architect.
Owner (asking): PM/UX (`claude-pm-ux-opus47`).
Context: [`PRODUCT_VISION.md`](../PRODUCT_VISION.md) requires the
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

---

> Append new questions above this line, newest on top.
