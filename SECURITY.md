# Security

`django-admin-react` sits in front of the Django admin and exposes a REST
API that any logged-in staff member can use. That position makes it a
high-value target. Every contribution must read this file before adding or
changing API behavior.

## 1. Reporting a vulnerability

Please **do not open a public GitHub issue** for security problems.

Email: `security@<TO-BE-CONFIGURED>` — until this is configured, open a
private GitHub Security Advisory on this repository
(`Security → Advisories → New draft advisory`).

We will respond within 5 working days. Critical issues will be patched as
soon as possible and a CVE requested where appropriate.

## 2. Threat model (v1)

We protect against:

- An unauthenticated attacker discovering models, fields, or data.
- A logged-in non-staff user reaching the API.
- A logged-in staff user using the API to bypass ModelAdmin-level
  restrictions (`has_*_permission`, `exclude`, `readonly_fields`).
- A logged-in staff user causing accidental data loss through requests the
  HTML admin would have prevented (CSRF, unconfirmed deletes via direct
  links).
- Sensitive fields (passwords, tokens, hashes) leaking through the list or
  detail responses.

Out of scope for v1:

- Defending an admin user against themselves at the model level (we trust
  the consumer's `ModelAdmin` and Django's user model). If staff is
  compromised, the admin is compromised — this is also true of
  `django.contrib.admin`.
- Rate limiting / brute-force protection on login (that's the consumer's
  job; we never replace the login flow).

## 3. Non-negotiable security rules

These are enforced by code review and by tests. A PR that violates any of
them must not merge.

1. **All API views require authenticated staff users by default.**
   The default permission class checks
   `user.is_active and user.is_staff and admin_site.has_permission(request)`.
2. **CSRF is on for unsafe methods.** We use Django's session-backed CSRF.
   We never disable CSRF on our endpoints, even "just for testing". The
   test client uses `csrf_checks=True`.
3. **Never expose models that are not registered in the admin site
   resolved via the configured `ADMIN_SITE`.** Look up models through
   `admin.site._registry` exclusively.
4. **Never trust client-provided `app_label`/`model_name`/field names.**
   Always look them up in the registry and the resolved
   `ModelAdmin.get_form()` fields. Unknown values return `404` (model) or
   `400` (field).
5. **Never bypass `ModelAdmin` permissions.** Use
   `has_view_permission`, `has_add_permission`, `has_change_permission`,
   `has_delete_permission`, and `has_module_permission`. Per-object checks
   pass the object instance.
6. **Never expose fields excluded by the admin form.** The set of writable
   fields = the form's `Meta.fields` minus `readonly_fields` minus
   `exclude`. The set of readable fields is similarly derived from
   `get_fields(request, obj)`/`get_fieldsets(...)`.
7. **Never serialize passwords, tokens, API keys, or other secret-shaped
   fields.** A denylist of common patterns lives in
   `api/serializers.py` and is applied **on top of** the
   `exclude`/`readonly_fields` rules (defense in depth). Documented in
   `docs/api-contract.md`.
8. **Writes always go through the admin form.** Create and update must
   instantiate `ModelAdmin.get_form(request, obj=...)` and call
   `form.is_valid()`. No manual `setattr(obj, field, ...)` from JSON.
9. **Deletes always go through `ModelAdmin.delete_model`.** This preserves
   any pre/post delete signals, audit logging, or cleanup the consumer
   wired up.
10. **No `Model.objects.all()` in API code.** Start from
    `ModelAdmin.get_queryset(request)` and chain further filters from
    there.
11. **No detail/list mass assignment.** If the form does not bind a field,
    the API does not accept it. Extra keys in payloads are rejected with
    `400`.
12. **`HttpResponseForbidden` on permission failures, not `404`.** Except
    for unregistered or non-existent objects (genuine `404`).

## 4. Required tests

Every endpoint added must include all of these tests before merging:

- Anonymous request → `302` to login or `403` (no body leakage).
- Authenticated **non-staff** user → `403`.
- Staff user without per-model permission → `403`.
- Staff user with permission → `200`/`201`/`204` as appropriate.
- Unregistered `app/model` → `404`.
- Bogus `pk` → `404`.
- Write attempts to `exclude`/`readonly` fields → `400` and value
  unchanged.
- CSRF token missing on unsafe method → `403`.
- Serializer never returns a field whose name matches the secret denylist
  (parametrized over a sample model with a `password` and `api_key`
  field).
- Permission booleans returned by list/detail match the truth from the
  `ModelAdmin` (no drift between UI hint and gate).

## 5. Secrets in the repository

- `.env`, `*.pem`, `*.key`, and `secrets/` are gitignored.
- Never paste a token, password, or API key into any file in this repo
  (including `forum/`, `docs/agents/`, PR descriptions, commit messages).
- If a secret is accidentally committed, the response is:
  1. Rotate the secret immediately.
  2. Force-push a rewritten history that removes the secret (and notify
     downstream consumers).
  3. File an entry in `docs/agents/changelog.md` describing what happened
     and what was rotated.
- The CI does a `gitleaks`-style scan on every PR.

## 6. Dependencies

- We pin direct dependencies in `pyproject.toml` and lock with Poetry.
- We pin direct frontend dependencies with pnpm's lockfile.
- A Dependabot/Renovate config (added in PR #2) keeps them current.
- Major version bumps require explicit review.

## 7. Build & release

- The PyPI artifact is built in CI from a tagged commit.
- The PyPI token lives in repository secrets, not in any file.
- A release requires a maintainer to approve the publishing job — CI never
  publishes on every merge.
- TestPyPI may be used for verification by maintainers but is also
  human-approved.

## 8. Static analysis

CI runs:

- `ruff` for lint (includes `S` security rules).
- `mypy` (best-effort; tightening planned for v1.x).
- `bandit` on the package source.
- `pip-audit` on the locked dependencies.
- Frontend: `eslint` (with `eslint-plugin-react`, `-jsx-a11y`,
  `-security`), `tsc --noEmit`.

## 9. Disclosure timeline

For valid vulnerability reports we aim for:

- Acknowledgement: ≤ 5 working days.
- Triage + reproducer: ≤ 14 calendar days.
- Patched release: depends on severity; critical issues are prioritized
  immediately.
- Public advisory: published with the fix, crediting the reporter unless
  they request anonymity.
