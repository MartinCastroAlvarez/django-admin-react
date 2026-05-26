# PR #3 — registry endpoint — Author claim

Posted: 2026-05-25
Agent id: `claude-author-opus47-pr03`
Role (per `docs/agents/pr-workflow.md` §1): **Author**
Branch: `pr/03-registry-endpoint` (based on `chore/foundation-pr1-opus47`,
stacked — will rebase onto `main` when PR #1 merges)

## Scope

Implement `GET /api/v1/registry/` per `docs/api-contract.md` §2.
Files in scope:

- `django_admin_react/api/permissions.py` — staff + `AdminSite.has_permission` gate.
- `django_admin_react/api/registry.py` — introspection helpers
  (resolve `ADMIN_SITE`, iterate `_registry`, build the response payload).
- `django_admin_react/api/views/registry.py` — the view (`RegistryView.get`).
- `django_admin_react/api/urls.py` — wire `path("registry/", ...)`.
- `tests/test_project/` — minimal Django project (settings, urls,
  conftest hooks) needed because `pyproject.toml` already declares
  `DJANGO_SETTINGS_MODULE = "tests.test_project.settings"`.
- `tests/test_registry.py` — full test matrix from `SECURITY.md` §4
  and `CLAUDE.md` §6 applied to the registry endpoint.

Out of scope for this PR:

- List / detail / write endpoints (PR #4, PR #5).
- SPA index view (PR #6).
- Anything that touches `SECURITY.md`, `LICENSE`, `docs/api-contract.md`,
  `pyproject.toml` deps, or `.github/workflows/*`.

## Tier estimate

**Tier 3** per `docs/agents/autonomy-policy.md`: new backend logic
inside `django_admin_react/`, no security-surface change.
**Caveat:** the file uses `ModelAdmin.has_module_permission` and
`has_view_permission`. The policy line "imports / configures CSRF,
session, login, or `ModelAdmin.has_*_permission`" is ambiguous — I read
it as "imports/configures **the definitions of** these methods", not
"calls these methods", because otherwise every endpoint is tier 5 and
the tier table is unusable. I'll flag this in
`docs/agents/open-questions.md` so a future PR can disambiguate.

If a reviewer disagrees and rules tier 5, default to higher per §5 of
the workflow doc — human review required.

## Test matrix I'll ship

- Anonymous → 302 (login redirect) or 403, no model names in body.
- Authenticated non-staff → 403.
- Staff but `AdminSite.has_permission` returns False → 403.
- Staff with permission → 200, payload shape matches contract.
- A model whose `ModelAdmin.has_module_permission` returns False is
  absent from `apps[*].models`.
- A model whose `ModelAdmin.has_view_permission` returns False is
  absent.
- A model not registered with the configured admin site is absent
  (even if registered with a different site).
- `mount` reflects the URL the request came in on, not a hardcoded
  path.
- CSRF: GET does not require it; response works without `X-CSRFToken`.
- The serializer never returns a `password` / `api_key` shaped field
  (parametrised; defense-in-depth — registry doesn't return field
  values anyway, but the test is cheap).

## Two-agent rule

Per workflow §3: I am the Author and will not review or merge this
PR. Reviewers welcome; please pick a different session id. The Merger
must also be a third session.

## gh auth note

Local `gh` is authed as `<gh-cli-account>`, who cannot see the
`MartinCastroAlvarez/django-admin-react` repo. `git push` works because
the remote URL embeds a different PAT. I will push the branch but the
human will need to fix `gh auth` (or add the `<gh-cli-account>` as a repo
collaborator) before any `gh pr create / review / merge` calls work.

— `claude-author-opus47-pr03`
