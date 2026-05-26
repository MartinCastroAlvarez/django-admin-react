# Threat model

> Companion to [`SECURITY.md`](../SECURITY.md) (the contract) and
> [`ACCEPTANCE.md`](../ACCEPTANCE.md) §4 (the measurable criteria).
> This document is the **STRIDE pass** per endpoint group: what we
> defend against, how, and what tests prove it.
>
> Owner: Security & Compliance Lead. Reviewed on every endpoint PR.

---

## 1. System under threat

```
                  ┌────────────────────────────────┐
attacker (web) ──►│ Browser (React SPA, untrusted) │── session+CSRF ──►┐
                  └────────────────────────────────┘                   │
                                                                       ▼
                                         ┌─────────────────────────────────────────┐
                                         │ Django process (consumer's project)     │
                                         │  ├─ session middleware                  │
                                         │  ├─ CSRF middleware                     │
                                         │  ├─ auth middleware                     │
                                         │  └─ django_admin_react.urls             │
                                         │       └─ api/v1/<endpoint>              │
                                         │            ↓ permissions.is_admin_user  │
                                         │            ↓ admin.site._registry       │
                                         │            ↓ ModelAdmin.<method>        │
                                         │                  ↓                      │
                                         │            consumer ORM                 │
                                         └─────────────────────────────────────────┘
```

Trust boundaries (each one is enforced before the next):

1. **Network** → request must terminate over the consumer's HTTPS.
2. **Session cookie** → must validate via Django's session middleware.
3. **CSRF token** (unsafe methods only) → must validate via Django's
   CSRF middleware.
4. **`permissions.is_admin_user`** → `is_active AND is_staff AND
   admin_site.has_permission(request)`.
5. **`admin.site._registry`** → only registered models progress to
   business logic; client strings are resolved here.
6. **`ModelAdmin.has_*_permission`** → model- and object-level gate
   for the specific operation.
7. **`ModelAdmin.get_queryset` / `get_form` / `delete_model`** → the
   data layer's own gate.

A flaw at any single layer must be caught by **at least one other**
layer (defense in depth). This document maps each STRIDE category to
the layer(s) responsible.

---

## 2. Assets

| ID  | Asset                                          | Sensitivity            |
| --- | ----------------------------------------------- | ---------------------- |
| A-1 | Consumer's domain data (any field of any model the admin exposes) | High |
| A-2 | Field values the admin form excludes / marks readonly | Higher (already gated) |
| A-3 | Password hashes, tokens, API keys, secret-shaped fields | Critical (never serve) |
| A-4 | User session cookies / CSRF tokens             | Critical               |
| A-5 | Authenticated user identity (id, email, etc.)  | Medium                 |
| A-6 | Schema knowledge (model and field names)       | Low–Medium (depends on consumer) |
| A-7 | The built React SPA bundle itself              | Medium (supply-chain target) |

---

## 3. Adversaries

| ID  | Adversary                                                         | Capability                              |
| --- | ----------------------------------------------------------------- | ---------------------------------------- |
| T-1 | Unauthenticated internet attacker                                 | Arbitrary HTTP; no session.              |
| T-2 | Authenticated non-staff user (e.g., regular consumer account)     | Valid session, no admin permission.      |
| T-3 | Low-privilege staff user (model X view-only, no change/delete)    | Valid session + staff, limited model perm. |
| T-4 | Compromised browser session (XSS in another consumer page)         | Can issue same-origin fetches with the session cookie. |
| T-5 | Supply-chain attacker (compromised npm/pip dep, MITM on bundle)    | Modifies bundled JS / a dep release.     |
| T-6 | Malicious / curious dev with commit access                         | Submits a PR; subject to multi-agent review. |
| T-7 | Compromised maintainer (someone with PyPI publish rights)          | Out of scope; mitigated by human-gated release tier. |

---

## 4. STRIDE per endpoint group

For each endpoint group we enumerate **Spoofing / Tampering /
Repudiation / Information Disclosure / Denial of Service / Elevation
of Privilege**. Each row points at the criterion (S-N) and the test
that proves it.

### 4.1 `GET /api/v1/registry/` (PR #3, on `main` today)

| STRIDE | Threat                                                                | Mitigation                                                                                          | Acceptance | Test |
| ------ | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------- | ---- |
| S      | T-1 / T-2 forges a session and reads the registry                     | Django session middleware (out of our scope); we enforce `is_authenticated and is_active and is_staff`. | S-1 / S-2 / S-3 | `test_registry.py::test_anonymous_is_rejected`, `test_non_staff_authenticated_is_403` |
| T      | T-3 tampers query string to enumerate apps they shouldn't see          | Endpoint takes no query params; filter is `iter_visible_models`.                                     | S-8        | `test_registry.py::test_registry_filters_by_has_view_permission` |
| R      | T-3 acts without an audit trail                                        | Out of scope for the registry endpoint (read-only). Logged via consumer's request middleware if any. | n/a        | n/a  |
| I      | T-1 / T-2 leaks model / field names via 403 body                       | `_FORBIDDEN_BODY` is fixed: `{"error":{"code":"forbidden","message":"You do not have permission."}}`. | S-1 / S-30 | `test_security.py::test_s1_anonymous_body_has_no_model_or_field_leak` |
| D      | T-1 storms the endpoint                                                | Out of scope for the package; document `django-ratelimit` in `docs/installation.md`. (See QSEC-2026-05-25-01.) | n/a | n/a |
| E      | T-3 toggles `has_view_permission` via a poisoned ModelAdmin subclass   | The package never instantiates consumer ModelAdmins itself — it reads `_registry` instances. If a consumer's `ModelAdmin` is malicious, that's a consumer-side issue (out of scope; documented in `SECURITY.md` §1). | n/a | n/a |

**Status:** registry is hardened. Tests cover the highlighted rows.

### 4.2 `GET /api/v1/<app>/<model>/` (list, lands in PR #4)

| STRIDE | Threat                                                            | Mitigation                                                                                    | Acceptance | Test (forward) |
| ------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------- | -------------- |
| S      | T-1 forges session                                                | Same gate as registry.                                                                         | S-1        | `test_list.py::test_anonymous_rejected` |
| T      | T-3 injects `app/model` to access unregistered model              | Resolve via `admin.site._registry`; unknown → 404, never `import_string`.                      | S-11 / S-12 | `test_list.py::test_unregistered_model_404` |
| T      | T-3 injects `ordering=` token to inject ORM fields                | `_validate_ordering(request, qs, raw)` allow-list against `get_ordering(request)`.             | S-19       | `test_security.py::test_ordering_injection_dropped` |
| T      | T-3 sends huge `page_size`                                        | Clamp to `MAX_PAGE_SIZE`.                                                                      | S-18       | `test_list.py::test_page_size_clamped` |
| R      | T-3 enumerates by repeated search                                 | Search delegates to `ModelAdmin.get_search_results` — same as HTML admin.                      | S-16       | `test_list.py::test_search_delegates_to_admin` |
| I      | T-3 sees fields the admin form excludes                           | `list_display` comes from `get_list_display(request)`; serializer enforces denylist on top.    | S-23 / S-31 | `test_list.py::test_excluded_field_not_serialized` |
| I      | T-3 sees password / token via list                                 | Sensitive-field denylist (S-31).                                                              | S-31       | `test_security.py::test_s31_denylist_constant_exists_and_complete` |
| D      | T-3 forces N+1 queries via crafted search                         | Forward to `get_search_results`; consumer's admin is the source of truth. Document for ops.    | n/a        | n/a |
| E      | T-3 sees objects outside their `get_queryset`                      | Start from `ModelAdmin.get_queryset(request)`; `Model.objects.all()` is **forbidden** in api/. | S-15       | `test_security.py::test_s15_no_objects_all_or_filter_in_api` |

### 4.3 `GET /api/v1/<app>/<model>/<pk>/` (detail, lands in PR #4)

Same matrix as list with these additions:

- **Information disclosure of "does object X exist?"** → return 404
  whenever the object is not in `get_queryset(request)`, regardless
  of whether it exists in the database. S-17.
- **Information disclosure via field set** → serialise only the
  fields the admin form declares; intersected with `get_fields`. S-23.
- **Information disclosure under DEBUG=True** → serializer must not
  expose `_state`, `Meta.private_fields`, or repr() of unhandled
  types. S-35 / S-36.

### 4.4 `POST` / `PATCH` (create, update, land in PR #5)

| STRIDE | Threat                                                            | Mitigation                                                                                    | Acceptance |
| ------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------- |
| S      | T-4 forges a same-origin write via XSS-controlled cookie          | CSRF token must be present and valid. **Mandatory.**                                          | S-26 / S-27 |
| T      | T-3 sets fields that are `readonly_fields` / `exclude`            | Form drops unknown fields; explicit-set returns 400 with `forbidden_field`.                   | S-22 / S-23 |
| T      | T-3 mass-assigns by sending extra keys                            | Form is the only writer; `setattr` from JSON is forbidden by lint (`test_s15` family + S-20). | S-20       |
| T      | T-3 sends arbitrary types (e.g., dict for an `IntegerField`)      | Form validation rejects.                                                                       | n/a        |
| R      | T-3 mutates without an audit trail                                | Reuse `LogEntry` via `ModelAdmin.log_change/log_addition` once write endpoints land.          | QSEC-02 (open) |
| I      | T-3 reads back a sensitive field via response after `PATCH`        | Response uses the same serializer with denylist (S-31).                                       | S-31       |
| D      | T-3 floods PATCH requests                                          | Out of scope; document rate-limiting recommendation. (QSEC-01)                                 | n/a        |
| E      | T-3 escalates by setting `is_staff=True` on a `User` row           | `User`'s ModelAdmin form on the consumer side controls this; package follows its `exclude`.    | S-22       |

### 4.5 `DELETE` (lands in PR #5)

| STRIDE | Threat                                                            | Mitigation                                                                                    | Acceptance |
| ------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------- |
| S      | T-4 forges a delete via XSS                                       | CSRF required.                                                                                 | S-26       |
| T      | T-3 deletes via PK they shouldn't access                          | Object resolved via `ModelAdmin.get_queryset(request)`; 404 outside.                          | S-17       |
| R      | T-3 deletes without trail                                          | `ModelAdmin.delete_model` calls the consumer's signals + `log_deletion`.                       | S-24       |
| I      | n/a (response is 204)                                              |                                                                                                | n/a        |
| D      | T-3 mass-deletes                                                   | One PK per request in v1 (no bulk endpoint). Bulk lands in v1.x with its own permissions.      | n/a        |
| E      | T-3 deletes a related object via cascade                           | Consumer-defined `on_delete`; out of our scope. Document.                                      | n/a        |

### 4.6 SPA shell (`SpaIndexView`, lands in PR #6)

| STRIDE | Threat                                                            | Mitigation                                                                                    | Acceptance |
| ------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ---------- |
| S      | T-1 sees the SPA without auth and learns mount-point structure    | Same `is_admin_user` gate before rendering.                                                    | S-1        |
| T      | T-5 swaps a malicious JS at the CDN                                | Subresource Integrity hashes on `<script>` / `<link>` injected by `scripts/build.sh`.          | QSEC-04 (open) |
| I      | The injected `<meta name="dar-mount">` leaks more than the mount  | The view sets exactly one meta tag with the resolved mount string (escaped).                  | S-29       |
| E      | T-4 reads `csrftoken` cookie via JS to issue forged requests       | `csrftoken` is not `HttpOnly` (by design — the SPA needs it). Mitigation is upstream CSP + same-site cookies. | S-65       |

---

## 5. Supply-chain

- **Python dependencies:** `pyproject.toml` runtime deps are limited
  to Django (`>=5.0,<6.0`). Dev-only deps (ruff, mypy, pytest, etc.)
  do not ship in the wheel. `pip-audit` runs in `scripts/audit-deps.sh`.
- **JS dependencies:** Frontend dev tooling only; nothing under
  `frontend/` is shipped on PyPI. The **built bundle** is shipped.
  `pnpm audit --prod` runs in `scripts/audit-deps.sh`.
- **Bundle integrity:** SRI hashes on the SPA's `<script>` / `<link>`
  tags (QSEC-04). Builds are reproducible (Vite emits deterministic
  hashes given the same input lockfile).
- **Release pipeline:** `scripts/deploy.sh` refuses without
  `POETRY_PYPI_TOKEN_PYPI`. Token is in env only; never echoed; never
  committed. Release is human-gated (tier 6).

---

## 6. Logging / privacy

- Package logger is `django_admin_react`. Never logs:
  - request bodies, response bodies
  - cookies, `Authorization` / `X-CSRFToken` headers
  - query strings (full URL is fine; raw `?q=...` value is not)
  - password / token / api_key field values
- Consumer is responsible for global access logs and request-id
  middleware. We document a recommended structure in
  `docs/installation.md` (planned).

---

## 7. What's intentionally out of scope

- **Brute-forcing the login page** — Django's login view is the
  consumer's, not ours. Recommend `django-axes` / `django-defender`
  in `docs/installation.md`.
- **Insider abuse by an authorized staff user** — a staff user with
  legitimate access can read everything that `ModelAdmin` permits.
  This is the same trust model as the HTML admin.
- **Rate limiting** — document a `django-ratelimit` recipe; do not
  bundle a runtime dep. (QSEC-01.)
- **DDoS / WAF** — operational concern; document a recommended
  reverse-proxy setup.
- **Bypass via direct ORM** — out of our control if the consumer
  exposes another framework on top of the same DB. We protect our
  surface only.

---

## 8. Review cadence

This document is re-reviewed:

- Before every endpoint PR (the matrix gets a row).
- Before every release (the entire matrix is re-walked).
- Whenever a CVE is reported against Django or a direct dep.
- Whenever the autonomy policy changes.

The reviewer signs off via a PR review comment on the relevant PR
when the review pass is complete.
