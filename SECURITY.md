# Security

`django-admin-react` sits in front of the Django admin and exposes a REST
API that any logged-in staff member can use. That position makes it a
high-value target. Every contribution must read this file before adding or
changing API behavior.

## 1. Reporting a vulnerability

Please **do not open a public GitHub issue** for security problems.

The primary reporting channel is **GitHub Security Advisories** on this
repository:

> **[Security → Advisories → New draft advisory](https://github.com/MartinCastroAlvarez/django-admin-react/security/advisories/new)**

This route is preferred because:

- It is private end-to-end between reporter and maintainers.
- It allocates a CVE number when warranted.
- It produces the published advisory at fix-time without any manual
  re-keying of details.
- It does not depend on an email address that could change, expire,
  or be intercepted in transit.

No additional channel is currently configured. If GitHub Security
Advisories are not viable for you (for example, you do not have a
GitHub account, or the issue blocks repository access), contact the
project maintainer directly via the email listed on their public
GitHub profile and request a private channel.

We will acknowledge a report within 5 working days. Critical issues
will be patched as soon as possible and a CVE requested where
appropriate. See §11 for the full disclosure timeline.

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

- `.env`, `*.pem`, `*.key`, `*.crt`, and `secrets/` are gitignored.
- Never paste a token, password, or API key into any file in this repo
  (including `docs/agents/`, PR descriptions, Issues, Discussions, commit
  messages). **Partial / redacted token references** (e.g., `ghp_…XYZ`)
  are also forbidden and detected by the pre-commit hook +
  `tests/test_security.py`.
- If a secret is accidentally committed, the response is:
  1. Rotate the secret immediately on the upstream provider.
  2. **Wait for human approval** before rewriting history. No agent may
     `git push --force` autonomously. Once approved, force-push the
     rewritten history that removes the secret and notify downstream
     consumers.
  3. Open a GitHub Issue labelled `incident:secret-leak` describing what
     happened and what was rotated. The Issue itself is the durable
     record; an Issue with that label active is a "kill switch" entry
     that disables auto-merge per
     `docs/agents/autonomy-policy.md` §3.
- A pre-commit hook (`.pre-commit-config.yaml`) runs `gitleaks` plus a
  custom `pygrep` for partial token patterns. Enable it locally with:
  `pre-commit install`.

## 6. Dependencies

- Runtime dependencies are deliberately minimal: only Django
  (`>=5.0,<6.0`). No DRF, no auth framework, no JWT lib. See
  `ACCEPTANCE.md` §4.9 S-47.
- Dev dependencies are pinned in `pyproject.toml` and locked with Poetry.
  Frontend dev dependencies are locked with `pnpm-lock.yaml`.
- Every new third-party dependency (runtime **or** dev) requires a
  matching entry in `docs/agents/decisions.md` explaining why and what
  alternative was rejected.
- Run `./scripts/audit-deps.sh` before every release. CI is intentionally
  absent (repo-owner direction); the dep audit is a local gate that the
  Merger / Releaser owns.

## 7. Build & release

- The PyPI artifact is built locally via `./scripts/build.sh`:
  `pnpm install` → `pnpm -r typecheck` → `vite build` →
  copy bundle into `django_admin_react/{static,templates}/admin_react/`
  → `poetry build`. The wheel ships pre-built React assets so consumers
  do not need Node.
- The PyPI token lives in environment variables only
  (`POETRY_PYPI_TOKEN_PYPI`), never in any file in the repo. The token
  is **never** echoed or logged by `scripts/deploy.sh`.
- Releases require a **human maintainer** (tier 6 in
  `docs/agents/autonomy-policy.md`). Agents do not tag, do not publish,
  do not auto-bump the version.
- TestPyPI may be used for verification by the maintainer with a
  separate token; same hygiene rules apply.

## 8. Static analysis (local-only — no CI in v0.x)

Run via `./scripts/lint.sh`:

- `ruff` (includes `S` bandit-style security rules)
- `ruff format --check`
- `black --check`
- `isort --check-only` (`force_single_line=True`)
- `flake8`
- `pylint --errors-only` (with `pylint-django`)
- `mypy` (best-effort; tightening planned for v1.x)
- `bandit -r django_admin_react`
- `pytest -q` (including `tests/test_security.py`)
- Frontend: `prettier --check`, `pnpm -r typecheck`, `pnpm -r lint`
  (`eslint` wires up in PR #6).

Dependency audit runs separately via `./scripts/audit-deps.sh`
(see §6).

## 9. Recommended consumer settings

These are not enforced by the package — they are best-practice defaults
the consumer's Django project **should** set. The package never
overrides them.

```python
# settings.py

# Cookies
SESSION_COOKIE_SECURE  = True   # ACCEPTANCE §4.14 S-62
CSRF_COOKIE_SECURE     = True   # S-62
SESSION_COOKIE_HTTPONLY = True  # S-62 (CSRF cookie stays readable by JS by design)
SESSION_COOKIE_SAMESITE = "Lax" # CSRF defense in depth

# Transport
SECURE_HSTS_SECONDS            = 31_536_000   # S-63
SECURE_HSTS_INCLUDE_SUBDOMAINS = True         # S-63
SECURE_HSTS_PRELOAD            = True         # S-63 — only after HSTS is verified
SECURE_SSL_REDIRECT            = True         # if behind a TLS-terminating proxy

# Headers
X_FRAME_OPTIONS              = "DENY"   # clickjacking — S-64
SECURE_CONTENT_TYPE_NOSNIFF  = True     # S-65
SECURE_BROWSER_XSS_FILTER    = True     # S-65 (legacy IE; cheap to leave on)
SECURE_REFERRER_POLICY       = "same-origin"

# Optional but recommended
SESSION_COOKIE_AGE = 60 * 60 * 8   # 8h staff session (QSEC-05)
```

A `Content-Security-Policy` middleware (via `django-csp` or
equivalent) is recommended once the SPA is live; sample snippet will
ship in `docs/installation.md` alongside PR #6
(see `docs/agents/open-questions.md` QSEC-2026-05-25-03).

### File / image field storage

The package emits `value.url` for `FileField` and `ImageField` values
in the detail response. Whether that URL is appropriately gated
depends on the consumer's storage backend — the package never wraps
the URL with its own access check:

- **Signed-URL backends** (S3 with bucket-level access blocked, GCS
  with signed-blob URLs, a custom storage that returns a tokenised
  download path, …). The URL is time-bound and per-request; an
  unauthenticated reader who captures the URL out-of-band has it for
  the signing TTL only. No further consumer action needed beyond
  setting the storage's TTL conservatively (matching `SESSION_COOKIE_AGE`
  is a reasonable upper bound).
- **Local-storage backends** with `MEDIA_URL` pointing at the same
  domain as the admin. The URL is just a path under the consumer's
  static-files server. If `MEDIA_URL` is publicly readable (the
  default Django development configuration), then any logged-in
  staff user who can view the row can also share the file URL with
  anyone — including unauthenticated parties — and they can fetch
  the file. For production deployments where files should stay
  staff-only, put `MEDIA_URL` behind the same staff-gate as the
  rest of the admin: `django-private-storage`, an `nginx`
  `auth_request` to the Django session check, or a small
  Django view that reads `MEDIA_ROOT` and gates on
  `request.user.is_active and request.user.is_staff`.

This is the same disclosure surface Django's HTML admin ships with
(its `<a href="{{ field.url }}">` does not check the linked URL's
ACL either). The SPA does not change the posture; it does make the
URLs trivially scriptable against `/api/v1/<app>/<model>/<pk>/`,
which raises the operational stakes of `MEDIA_URL` configuration.

## 10. Cross-references

- [`ACCEPTANCE.md`](ACCEPTANCE.md) §4 — measurable security criteria.
- [`docs/threat-model.md`](docs/threat-model.md) — STRIDE pass per
  endpoint group.
- [`docs/agents/security-expert/AGENT.md`](docs/agents/security-expert/AGENT.md)
  — Security Lead role contract.
- [`docs/agents/security-expert/REVIEW_CHECKLIST.md`](docs/agents/security-expert/REVIEW_CHECKLIST.md)
  — what Security checks on every PR.

## 11. Disclosure timeline

For valid vulnerability reports we aim for:

- Acknowledgement: ≤ 5 working days.
- Triage + reproducer: ≤ 14 calendar days.
- Patched release: depends on severity; critical issues are prioritized
  immediately.
- Public advisory: published with the fix, crediting the reporter unless
  they request anonymity.
