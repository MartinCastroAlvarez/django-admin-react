# Security

`django-admin-react` is the **React SPA super-layer** on top of the
[`django-admin-rest-api`](https://github.com/MartinCastroAlvarez/django-admin-api)
package. The API package owns every wire-level gate (authn, authz,
queryset, serializer denylist, CSRF, write-form enforcement); this repo
owns the SPA-side concerns (CSP-friendly assets, no secret leakage in
the bundle, safe SPA mount, PWA boundaries, screenshot hygiene). Every
contribution must read this file before changing security-sensitive
behaviour in this repo.

> ### Where each security concern actually lives
>
> | Concern | Owned by | Reference |
> |---|---|---|
> | API authn / authz / CSRF / queryset / denylist / write enforcement | **`django-admin-rest-api`** repo | [its `SECURITY.md`](https://github.com/MartinCastroAlvarez/django-admin-api/blob/main/SECURITY.md) |
> | SPA: pre-built bundle integrity, no token/`.env` leakage in assets, PWA cache-on-logout, SPA mount safety | **This repo** | the rest of this file |
> | Supply chain (Dependabot, SHA-pinned actions, `pip-audit`) | Both repos | this file §6 and §13 |
> | Release publish (PyPI Trusted Publishing / token) | Both repos, owner-gated | this file §7 + the corresponding section in the API repo |
>
> During [META #544](https://github.com/MartinCastroAlvarez/django-admin-react/issues/544)
> the local `django_admin_react/api/` tree is still on `main` for a few
> more PRs; the rules below that mention API endpoints continue to
> apply **here** until that code is removed, and **in the API repo**
> permanently from that point on. Do not introduce a new API endpoint
> in this repo — open it in the API repo instead.

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
   fields.** A denylist of common patterns lives in the
   `django-admin-rest-api` package and is applied **on top of** the
   `exclude`/`readonly_fields` rules (defense in depth).
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
- Never paste a token, password, or API key into any file in this repo,
  PR description, Issue, Discussion, or commit message. **Partial /
  redacted token references** (e.g., `ghp_…XYZ`) are also forbidden and
  detected by the pre-commit hook.
- If a secret is accidentally committed: (1) rotate it immediately on
  the upstream provider; (2) request approval to rewrite history; (3)
  open a GitHub Issue labelled `incident:secret-leak` as the durable
  record.
- A pre-commit hook (`.pre-commit-config.yaml`) runs `gitleaks` plus a
  custom `pygrep` for partial token patterns. Enable it locally with:
  `pre-commit install`.

## 6. Dependencies

- Runtime dependencies are deliberately minimal: only Django
  (`>=5.0,<7.0`), the sibling
  [`django-admin-rest-api`](https://pypi.org/project/django-admin-rest-api/)
  (the JSON API), and the sibling
  [`django-admin-mcp-api`](https://pypi.org/project/django-admin-mcp-api/)
  (the MCP exposure of the same API). No DRF, no auth framework, no JWT
  lib — the API package reuses Django's session + CSRF; the SPA reuses
  the same.
- Dev dependencies are pinned in `pyproject.toml` and locked with Poetry.
  Frontend dev dependencies are locked with `pnpm-lock.yaml`.
- Every new third-party dependency (runtime **or** dev) goes through PR
  review explaining why and what alternative was rejected.
- Run `./scripts/audit-deps.sh` before every release.

## 7. Build & release

- The PyPI artifact is built locally via `./scripts/build.sh`:
  `pnpm install` → `pnpm -r typecheck` → `vite build` →
  copy bundle into `django_admin_react/{static,templates}/admin_react/`
  → `poetry build`. The wheel ships pre-built React assets so consumers
  do not need Node.
- The PyPI token lives in environment variables only
  (`POETRY_PYPI_TOKEN_PYPI`), never in any file in the repo. The token
  is **never** echoed or logged by `scripts/deploy.sh`.
- Releases require a **human maintainer**. The publish is driven by the
  `publish.yml` workflow (OIDC Trusted Publishing — no stored token);
  the maintainer triggers it by publishing a GitHub Release.
- TestPyPI may be used for verification by the maintainer with a
  separate token; same hygiene rules apply.

## 8. Static analysis (local + CI)

**The test suites run server-side in CI**
(`.github/workflows/ci.yml`): backend `pytest` and the frontend `pnpm`
gate (typecheck + lint + test + build), so a red suite cannot merge.

Enforcing the **Python lint gate** in CI is a near-term follow-up:
`scripts/lint.sh` currently runs two formatters (`ruff format` + `black`)
whose output conflicts, so it isn't satisfiable on a clean tree yet. The
local script below is still the authoritative lint gate; it gets
de-conflicted and the small existing debt cleared first, then the lint
step is added to CI.

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
- Frontend: `pnpm -r typecheck`, `pnpm lint` (eslint `--max-warnings 0`
  + stylelint + dark-mode coverage), `pnpm test` (vitest), `pnpm -r build`.

Making the CI checks **required** in branch protection is a separate
owner action (#452 / #331).

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

### Content-Security-Policy (recommended — QSEC-03)

The SPA shell (`templates/admin_react/index.html`) loads **only**
same-origin assets: one external ES-module bundle and its stylesheet
under your `STATIC_URL`, a `data:` favicon, the PWA manifest, and the
service worker — **no inline `<script>`**. That means a fairly strict
CSP is achievable, and `script-src 'self'` (no `'unsafe-inline'`) is the
load-bearing directive: it contains an XSS even if a consumer's
`ModelAdmin` accidentally `mark_safe()`s attacker-controlled data into an
HTML field value (the one consumer-trust boundary — see §2.7).

Apply it with [`django-csp`](https://django-csp.readthedocs.io/) or any
header middleware. A starting policy for the admin mount:

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';   # React/runtime inline style attrs
  img-src 'self' data:;               # data: favicon
  font-src 'self';
  connect-src 'self';                 # the API is same-origin
  manifest-src 'self';
  worker-src 'self';                  # the PWA service worker
  frame-ancestors 'none';             # clickjacking (with X_FRAME_OPTIONS)
  base-uri 'self';
  form-action 'self';
```

Caveats — **validate before enforcing**:

- Roll it out in **`Content-Security-Policy-Report-Only`** first and
  watch for violations; only switch to the enforcing header once clean.
- If you serve `FileField`/`ImageField` media or signed download URLs
  from a **different origin** (S3, GCS, a CDN), add that origin to
  `img-src` and `connect-src`.
- `style-src 'unsafe-inline'` is included because React sets inline
  `style` attributes at runtime; it is far lower-risk than allowing
  inline scripts. Drop it if you verify your build needs no inline
  styles.
- This policy assumes the package is mounted on its own path under your
  domain. If you already ship a project-wide CSP, **merge** these
  directives rather than replacing your policy.

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

#### Uploads (write side)

`FileField` / `ImageField` are now **writable** over `multipart/form-data`
(create + update). The package stores the file through the field's own
form + configured `Storage` — it never builds a path from the
client-supplied filename (`Storage.get_valid_name` / `get_available_name`
sanitise it, so path traversal can't escape `upload_to`), and an upload
addressed to a `readonly` / `exclude` / unknown field is rejected `400`.
Three things remain the **consumer's** responsibility:

- **Size / count limits — keep Django's defaults on.** The multipart parse
  enforces `DATA_UPLOAD_MAX_MEMORY_SIZE`, `FILE_UPLOAD_MAX_MEMORY_SIZE`, and
  `DATA_UPLOAD_MAX_NUMBER_FIELDS`; the package never raises or disables them
  (an over-limit upload returns a clean `400`). Do **not** set these to
  unbounded values, and tune them for the largest legitimate upload — they
  are your DoS guard against a worker streaming a multi-GB body.
- **Content validation is yours, by design.** The package stores whatever
  the field's validators accept; it does **not** sniff content (that would
  be a parallel system — `ModelAdmin` stays the source of truth). For
  untrusted uploads add field validators / extension allowlists / an AV
  scan, and prefer a storage location that can't execute what it holds.
- **Stored-file XSS.** A file served from the admin's own origin with a
  guessable URL and a dangerous content-type (HTML, SVG) is a stored-XSS
  vector. Serve media from a **separate origin** or with
  `Content-Disposition: attachment`, and keep `SECURE_CONTENT_TYPE_NOSNIFF`
  on (above). `ImageField` validation (Pillow) rejects non-images including
  SVG; plain `FileField` accepts anything its validators allow.

## 10. Cross-references

- The **API package's** own `SECURITY.md` in
  [`MartinCastroAlvarez/django-admin-api`](https://github.com/MartinCastroAlvarez/django-admin-api/blob/main/SECURITY.md)
  — every API-side concern (each `/api/v1/...` endpoint, the
  serializer denylist, the permission gates) lives there.
- [`README.md`](README.md) — install + three-repo cross-links.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — what lives in this repo
  vs. the API / MCP siblings.
- The **API package's** own `SECURITY.md` —
  [`MartinCastroAlvarez/django-admin-api`](https://github.com/MartinCastroAlvarez/django-admin-api/blob/main/SECURITY.md)
  — for every API-side gate (each `/api/v1/...` endpoint, the
  serializer denylist, the permission checks).

## 11. Disclosure timeline

For valid vulnerability reports we aim for:

- Acknowledgement: ≤ 5 working days.
- Triage + reproducer: ≤ 14 calendar days.
- Patched release: depends on severity; critical issues are prioritized
  immediately.
- Public advisory: published with the fix, crediting the reporter unless
  they request anonymity.
