# examples/jobs — Custom-form / legacy-iframe demo app

A single `Job` model whose `ModelAdmin` deliberately exercises the
**request-driven custom-view + custom-template** pattern that real Django
admins use — and which the React SPA cannot render from the JSON form-spec.
The point of this fixture: it uses *only* documented `ModelAdmin` hooks
(`formfield_for_dbfield`, an admin `action`, `change_view`, a custom
template). No django-admin-react / -rest-api / -mcp-specific API appears
anywhere. If this app works on `/admin-react/`, any legacy `/admin/`
ModelAdmin works too — with at most a single-view iframe fallback.

## What's here

- `models.py` — `Job(name, metadata: JSONField, status)`.
- `admin.py` — `JobAdmin` + `get_step_registry()`.
- `templates/admin/jobs/job/run_custom.html` — the dual-listbox UI.
- `tests/test_admin.py` — backend tests for both render paths and the
  ordered POST contract.

## The two rendering paths

**Path A — `/admin-react/jobs/job/<pk>/change/`** (no query)

The stock change form. `formfield_for_dbfield` swaps `metadata` to a large
textarea, so the form-spec endpoint returns `widget.kind == "textarea"` with
`vLargeTextField` in `widget.attrs.class`. The SPA renders this natively and
it matches the legacy `/admin/` change form field-for-field.

**Path B — `/admin-react/jobs/job/<pk>/change/?run_custom=1`**

`JobAdmin.change_view` branches on `request.GET` and `render()`s a hand-rolled
dual-listbox template — not a `ModelForm`, not fieldsets. There is no
form-spec to serialise, so the resolver returns:

```json
{ "renderer": "legacy-iframe",
  "legacy_url": "/admin/legacy/jobs/job/<pk>/change/?run_custom=1" }
```

The SPA renders its breadcrumb / sidebar / toolbar from the spec, then embeds
the legacy URL in an iframe for the body. The custom POST contract
(`request.POST.getlist("selected_steps")`, ordered) is preserved.

## Bonus: action → redirect → variant

The **Run (Custom)** admin action returns an `HttpResponseRedirect` to
`?run_custom=1`. The SPA action runner follows the redirect (the
action-redirect contract, #620), after which Path B kicks in.

## How it's validated across the three packages

| Layer | What it asserts | Where |
|-------|-----------------|-------|
| rest-api | Path A → `form-spec` w/ textarea; Path B → `legacy-iframe` | `tests/test_form_spec.py` |
| mcp | `admin.form_spec` forwards the `legacy-iframe` discriminator | `tests/test_integration.py` |
| react | SPA renders `LegacyIframe` on `renderer == "legacy-iframe"` | `frontend` + this app |

## Run the backend tests

```bash
poetry run python examples/project/manage.py test examples.jobs
```
