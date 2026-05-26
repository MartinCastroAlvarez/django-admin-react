# Security review checklist

The Security & Compliance Lead applies this checklist to every PR
before posting an `Approve` / `Request changes` / `Comment` review.

Reference: [`ACCEPTANCE.md`](../../ACCEPTANCE.md) §4, the role's
[`AGENT.md`](AGENT.md) "Mandatory invariants" section, and
[`SECURITY.md`](../../SECURITY.md).

Each line below is **binary**. If any item marked **[BLOCK]** fails,
the verdict is **Request changes**, not Approve. Items marked
**[NOTE]** become non-blocking comments + follow-up handoffs.

---

## 0. Tier triage (decide before doing the rest)

- [ ] Tier 1 (docs / forum / folder READMEs)
- [ ] Tier 2 (skeletons / stubs / typings)
- [ ] Tier 3 (backend code, no security surface)
- [ ] Tier 4 (frontend code)
- [ ] **Tier 5** (any of: `SECURITY.md`, `LICENSE`, `pyproject.toml`
      deps, frontend root `package.json` deps, `.github/workflows/`,
      CSRF/auth code, serializer denylist, `conf.py` defaults,
      new public URL patterns, the autonomy policy itself)
- [ ] **Tier 6** (release / publish)

Tier 5+ requires human approval **in addition** to my Security
review. For tier 5 PRs I never auto-merge; I post my review and the
human takes it from there.

---

## 1. Secret / token / credential hygiene (always)

- [ ] **[BLOCK]** `git diff --cached | grep -iE '(ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|aws_secret_access_key|begin (rsa|ec|openssh) private)'` returns nothing on the PR's diff.
- [ ] **[BLOCK]** No `.env` / `.env.*` / `*.pem` / `*.key` / `*.crt` is added or modified.
- [ ] **[BLOCK]** No partial token redactions (`ghp_…XYZ`) anywhere in the diff, even in markdown or forum posts.
- [ ] **[BLOCK]** No `git config` output, no `git remote -v` output, no `printenv` / `env` output in the diff.
- [ ] **[NOTE]** Any new env-var name introduced by the diff is documented (in the relevant README / `SECURITY.md`).
- [ ] **[NOTE]** Any new `os.environ[...]` access is documented as a config knob, not a secret.

## 2. Authentication & authorization

- [ ] **[BLOCK]** Every new or changed view consults
      `permissions.is_admin_user(request)` (or equivalent gate that
      chains through `AdminSite.has_permission`) **before** any
      model access. (ACCEPTANCE §4.1 S-1 … S-5)
- [ ] **[BLOCK]** Every new mutation view consults the matching
      `ModelAdmin.has_*_permission(request, obj=None)` and passes
      the object for object-level checks. (ACCEPTANCE §4.2 S-6, S-7)
- [ ] **[BLOCK]** No new code path uses `user.has_perm(...)`
      directly — always via `ModelAdmin`.
- [ ] **[BLOCK]** Frontend never trusts client-side `permissions`
      cache for **server** decisions — the backend re-checks every
      operation.
- [ ] **[NOTE]** If the diff adds a new public URL pattern under
      the package, confirm it sits behind the same gate.

## 3. Resource exposure (deny-by-default)

- [ ] **[BLOCK]** Models not in `admin.site._registry` return 404.
      The 404 envelope never reveals existence vs registration.
      (ACCEPTANCE §4.3 S-11 … S-14)
- [ ] **[BLOCK]** No `import_string`, `apps.get_model`, `__import__`,
      `getattr(module, name)` called on **client-supplied** strings.
- [ ] **[BLOCK]** No `admin.site.register(...)` or `@admin.register`
      in `django_admin_react/` (the package reads `_registry`, never
      writes).

## 4. Queryset protection

- [ ] **[BLOCK]** Every list / detail path starts from
      `ModelAdmin.get_queryset(request)`. No `Model.objects.all()` /
      `objects.filter()` in `django_admin_react/api/`. (ACCEPTANCE
      §4.4 S-15 … S-19)
- [ ] **[BLOCK]** Search uses `ModelAdmin.get_search_results(...)`.
- [ ] **[BLOCK]** Detail fetch uses
      `get_queryset(request).get(pk=...)` (not `Model.objects.get`).
- [ ] **[NOTE]** Page size is clamped to `MAX_PAGE_SIZE` (default
      200). If the diff changes this, it has a decision entry.

## 5. Forms & writes

- [ ] **[BLOCK]** Create / update go through
      `ModelAdmin.get_form(request, obj)` + `form.is_valid()`. No
      `setattr(obj, name, json_value)`. (ACCEPTANCE §4.5 S-20…S-25)
- [ ] **[BLOCK]** PATCH merges initial-from-instance with incoming
      payload, then validates.
- [ ] **[BLOCK]** Fields in `get_readonly_fields` and `get_exclude`
      cannot be written. 400 on attempt; value unchanged.
- [ ] **[BLOCK]** DELETE calls `ModelAdmin.delete_model(...)`. No
      `obj.delete()` shortcuts.

## 6. CSRF, session, cookies

- [ ] **[BLOCK]** No `@csrf_exempt` anywhere in the diff.
- [ ] **[BLOCK]** Unsafe methods (`POST` / `PATCH` / `PUT` / `DELETE`)
      reject missing or invalid `X-CSRFToken` with 403. (ACCEPTANCE
      §4.6 S-26 … S-30)
- [ ] **[BLOCK]** SPA shell view sets the CSRF cookie via Django's
      middleware (`@ensure_csrf_cookie` or equivalent).
- [ ] **[BLOCK]** No `request.session[...] = ...` writes from the
      package. No reads of `SESSION_COOKIE_*` to override Django.
- [ ] **[NOTE]** Permission-denied responses include
      `Cache-Control: no-store`.

## 7. Serialization (defense in depth)

- [ ] **[BLOCK]** The sensitive-field denylist exists, matches at
      least `password / secret / token / api_key / apikey / hash /
      private_key / session / nonce / salt`, case-insensitive,
      substring match. **Applied on top of** the admin's `exclude`
      and `readonly_fields`. (ACCEPTANCE §4.7 S-31 … S-36)
- [ ] **[BLOCK]** Unknown / unhandled types fall back to `str(value)`
      (never `repr(value)`).
- [ ] **[BLOCK]** ForeignKey → `{id, label}`, no nested object.
- [ ] **[BLOCK]** ManyToMany → `type: "unsupported"`, never editable
      in v1.
- [ ] **[BLOCK]** No `model._meta.private_fields` usage for output.

## 8. API hardening / logging

- [ ] **[BLOCK]** No `/api/v1/__debug__/`-style endpoints.
- [ ] **[BLOCK]** No default open CORS in the package
      (`django-cors-headers` is the consumer's call).
- [ ] **[BLOCK]** 500 envelope never includes stack trace, exception
      message, or raw payload — even under `DEBUG=True`.
- [ ] **[BLOCK]** `PUT` / `TRACE` / `CONNECT` return 405.
- [ ] **[BLOCK]** Logs do not include request bodies, response
      bodies, cookies, `Authorization` / `Cookie` / `X-CSRFToken`
      headers, or full query strings.

## 9. Tests

- [ ] **[BLOCK]** For every new / changed endpoint, the matrix in
      ACCEPTANCE §4.15 is fully covered in `tests/test_security.py`
      (or the endpoint-specific test file with explicit reference).
- [ ] **[BLOCK]** No `@pytest.mark.skip` / `@pytest.mark.xfail` on
      a security test without a linked GitHub issue and human
      approval.
- [ ] **[NOTE]** Coverage for `permissions.py` and `serializers.py`
      is at 100 % statements + branches; for `views/*` ≥ 95 %.

## 10. Dependencies

- [ ] **[BLOCK]** Any addition / removal / bump in `pyproject.toml`
      runtime deps or `frontend/**/package.json` deps has a
      `docs/agents/decisions.md` entry.
- [ ] **[BLOCK]** `poetry run pip-audit` returns 0 findings of
      severity ≥ HIGH (run after `poetry lock`).
- [ ] **[BLOCK]** `pnpm audit --prod` returns 0 findings of
      severity ≥ HIGH (in `frontend/`).
- [ ] **[BLOCK]** No new runtime dep on `djangorestframework`,
      OAuth / JWT libraries, or any auth framework.

## 11. PII / fixtures / examples

- [ ] **[BLOCK]** No real emails, phone numbers, IBANs, card
      numbers, addresses, or names in `tests/**` and `examples/**`
      fixtures.
- [ ] **[BLOCK]** Example apps use clearly synthetic identifiers
      (Alice / Bob / Carol, `example.com`, fake IBAN tagged
      `# fake`).

## 12. Release & publishing (tier 6 only)

- [ ] **[BLOCK]** `scripts/deploy.sh` refuses to run without
      `POETRY_PYPI_TOKEN_PYPI`; never echoes it.
- [ ] **[BLOCK]** Released wheel embeds the pre-built SPA only; no
      `frontend/`, `node_modules/`, or `*.ts` / `*.tsx` in the
      wheel.
- [ ] **[BLOCK]** Human approval is the trigger. Agents do not tag
      or publish.

## 13. Cross-role handoffs

- [ ] **[NOTE]** If the PR creates a cross-role dependency
      (e.g., this PR exposes a new endpoint that needs Architect
      perf review), open a handoff in
      the Issue queue.
- [ ] **[NOTE]** If the PR resolves a handoff to Security, mark it
      `done` in the same diff.

---

## How I post the review

1. Run the checklist locally.
2. Post the review using
   `gh pr review <N> --approve / --request-changes / --comment`.
3. The review body **must**:
   - Cite the ACCEPTANCE.md / SECURITY.md sections checked.
   - Quote specific file + line for every requested change.
   - Be at least one sentence — never just "LGTM" or "👍".
4. If the verdict is `Request changes`, drop a forum file
   the PR review comment
   summarising the changes asked for.
5. If the verdict is `Approve` on a tier-5 PR, the body says
   "Approved subject to human sign-off — tier 5 requires repo
   owner approval before merge."

## Anti-patterns I block

- "We'll add tests in a follow-up PR."
- "It's only a refactor, no review needed."
- "CI will catch it." (We have no CI.)
- "The frontend handles it." (Defense in depth; backend must enforce.)
- "It's behind staff auth." (Necessary, not sufficient — the
  backend still must obey `ModelAdmin`.)
- "`# noqa: S101`" on a security-relevant rule. (Open an issue
  instead.)
