# DECISIONS — Security & Compliance Lead

Durable decisions made under this role. Append-only. Mirror each
entry to `docs/agents/decisions.md` with the `[SEC]` tag so other
agents see it without reading this folder.

---

## 2026-05-25 — Bootstrap

- **Security acceptance lives in `ACCEPTANCE.md` §3, owned solely by
  this role.** PM and Architect get their own sections (§1, §2).
  No agent may edit another's section without a counter-claim posted
  in `forum/` first. — `ACCEPTANCE.md` header
- **Sensitive-shaped field denylist (defense in depth) is fixed at
  `password`, `secret`, `token`, `api_key`, `apikey`, `hash`,
  `private_key`, `session`, `nonce`, `salt`.** Applied **on top of**
  the admin form's own exclusion rules — never as a substitute.
  Codified in `SECURITY.md` §2.7 and (when implemented) in
  `django_admin_react/api/serializers.py`. — invariant
- **Deny-by-default for resource lookup.** Any client-supplied
  `app_label`, `model_name`, or field name that fails to resolve
  through `admin.site._registry` returns `404`, not `400`. This
  prevents enumeration. — invariant
- **403 envelopes never leak existence.** Permission-denied responses
  for an object the user can't view return the **same** body as the
  same response for a non-existent object only when the object
  exists; for non-existent objects we return `404`. The split is:
  *we admit existence only if the user has view permission.*
  — `docs/api-contract.md` §6 + `SECURITY.md` §3
- **CSRF is mandatory.** No view in the package is `@csrf_exempt`.
  Tests must assert that a missing or invalid `X-CSRFToken` header
  on `POST` / `PATCH` / `DELETE` returns `403`. — invariant
- **No CI in v1.** The Merger runs `scripts/lint.sh` locally; security
  scans (`ruff S`, `bandit`, `pip-audit`, secret grep) are part of
  that script. Acceptance criteria below treat the local pipeline as
  authoritative until CI is reintroduced. — repo-owner directive
- **Frontend never holds permission state alone.** `@dar/data` may
  cache `permissions: {view, add, change, delete}` from the API for
  UI courtesy (hide buttons), but **every** write call re-verifies
  on the backend. Cached permissions in `localStorage` are
  invalidated on any 401/403 response. — `ARCHITECTURE.md` §5.2a,
  `docs/data-layer.md`

---

> Append new decisions above this line, newest on top. Each entry:
> one to two lines, link to the file / section that records the
> contract.
