# DECISIONS — Security & Compliance Lead

Durable decisions made under this role. Append-only. Mirror each
entry to `docs/agents/decisions.md` with the `[SEC]` tag so other
agents see it without reading this folder.

---

## 2026-05-25 — Bootstrap

- **Security acceptance lives in `ACCEPTANCE.md` §3, owned solely by
  this role.** PM and Architect get their own sections (§1, §2).
  No agent may edit another's section without a counter-claim posted
  in an Issue first. — `ACCEPTANCE.md` header
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
- **The gate runs locally and in CI.** `scripts/lint.sh` is the local
  gate; `.github/workflows/ci.yml` runs that same script (plus the
  frontend gate) server-side on every PR so a red suite can't merge
  (#452 — the earlier "no CI" stance was reversed). Security scans
  (`ruff S`, `bandit`, the pre-commit secret/pygrep hooks) run in both;
  `pip-audit` stays a local pre-merge step (§6). — #452
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
