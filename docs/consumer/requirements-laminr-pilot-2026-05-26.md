# Consumer integration feedback — production-Django pilot (2026-05-26)

> Filed by a generic production Django + React integration team after a
> read-through of `0.1.0a1` and a pilot mount at a non-default admin
> path. The shop's domain, business, and internal model names are
> intentionally not described here — the requirements below are stated
> in terms of standard `django.contrib.admin` primitives so they apply
> to **any** consumer.

## 0. Context

A Django 5.2 application with:

- A **custom `AdminSite`** with project-wide overrides (login UX, branding,
  cross-app actions, custom permission gating).
- A custom **`ModelAdmin` base class** with shared decorators for
  `@admin.action` and batch-style operations.
- Heavy use of `inlines`, `list_filter`, `list_editable`,
  `autocomplete_fields`, `date_hierarchy`, file uploads, and custom
  `SimpleListFilter` subclasses.
- A mix of standard scalar fields, `JSONField`, M2M with extra `through`
  fields, and `FileField`.
- A mature legacy admin that operators use daily and rely on.

The library was mounted at a **second admin path** (`/admin2/`)
alongside `/admin/`, behind a settings dict pointing at the consumer's
custom `AdminSite`. That much works: the registry endpoint enumerates
the models the user can see, the list view paginates and searches, and
the detail view renders the form for simple scalar models. The
requirements below cover the **next ring out** — the features a real
admin needs before the SPA can replace the legacy UI on more than the
simplest leaf models.

## 1. Read-path requirements (list + detail)

### 1.1 Inlines — `#54`

`ModelAdmin.inlines` is silently dropped today. The detail response
should include an `inlines: []` array with each inline's child model,
fields, permissions, fieldsets, `extra`, `min_num`, `max_num`, and
`can_delete`. Inline edits should round-trip through the admin's
formset machinery so `clean()` hooks and signals still fire.

### 1.2 `list_filter` — `#56`

The left-sidebar filter bar of legacy admin (`BooleanField` toggles,
choice dropdowns, FK selectors, date ranges, `SimpleListFilter`
lookups) is the way non-engineer operators navigate big tables. The
SPA needs this declarative metadata, plus a documented URL grammar for
applying filters.

### 1.3 `date_hierarchy` — `#62`

`ModelAdmin.date_hierarchy = "created_at"` is the year/month/day
drill-down strip. Surface it as `date_hierarchy: {field,
granularity_options}` and accept narrowing query params with row
counts at each level.

### 1.4 ManyToMany read — `#55`

M2M fields currently return `type: "unsupported"`. Serialize them as
`[{id, label}, …]` with sane pagination, and surface the
`filter_horizontal` / `filter_vertical` hint so the SPA matches the
admin's widget choice.

### 1.5 Extended field type vocabulary — `#60`

`JSONField`, `ArrayField`, range types, `DurationField`,
`BinaryField`, IP fields, `FilePathField` should all be in the closed
type vocabulary with explicit serialize/parse rules. Plus a
`register_field_type(...)` hook so a custom field can plug in without
a fork.

### 1.6 File / image read — `#57`

Detail descriptors for `FileField` / `ImageField` should return
`{name, url, size}` (and `accept` MIME hint where the admin declares
one), so the SPA can render the current upload and a "replace / clear"
control.

## 2. Write-path requirements

### 2.1 File / image upload — `#57`

A `multipart/form-data` write path; the view passes `request.FILES`
into the admin form so existing storage backends keep working. A
documented "clear" convention (`{field: null}` or a sub-endpoint).

### 2.2 Bulk PATCH + `list_editable` — `#61`

`ModelAdmin.list_editable` should produce editable cells in the SPA
list view, backed by a `PATCH /api/v1/<app>/<model>/bulk/` endpoint
with per-row validation, an atomic transaction by default, and a
per-row error envelope.

### 2.3 Admin actions — `#58`

`ModelAdmin.actions` (`@admin.action`) is the operator's lever for
"do X across these N rows." Surface the action list and add an action
runner endpoint that re-resolves the action through the admin (never
trust the action name client-side), runs it over
`get_queryset(request).filter(pk__in=pks)`, and respects confirmation
flows.

### 2.4 ManyToMany write — `#55`

Accept `[pk1, pk2, …]` on create/update; route through
`form.save_m2m()`. Explicit "not supported" for `through` models with
extra fields is fine for a first cut.

## 3. UX / lookup ergonomics

### 3.1 Autocomplete / raw_id_fields — `#59`

A `?q=` autocomplete endpoint gated by the **target** model's
`has_view_permission`, driven by the target's `search_fields`. The
detail descriptor should declare `autocomplete: true` / `raw: true`
so the SPA picks the right widget.

### 3.2 Session expiry handling — `#63`

The SPA contract for "user was signed in, now they're not" needs to
be documented. Today every API call collapses to a generic 403; the
SPA can't tell the difference between "you never had a session" and
"your session expired five minutes ago." A distinct error code, a
documented re-login modal, and a `?next=<spa-path>` round-trip
restore the legacy admin's "you land back where you were" property.

## 4. Extensibility

### 4.1 Frontend extension points — `#65`

`ARCHITECTURE.md` is right that the SPA is metadata-driven. But every
real Django app eventually needs a per-model widget the closed
vocabulary can't describe (a JSON editor, a map, an audit-trail
panel, a custom button). A `registerFieldWidget` /
`registerModelPanel` / `registerModelAction` surface — small,
documented, append-only — converts "I had to fork the SPA" into "I
dropped one file in my app."

### 4.2 Machine-readable schema — `#64`

A `GET /api/v1/schema/` endpoint returning OpenAPI 3.1 (or JSON
Schema) for the envelope shapes — registry, list, detail, errors,
type vocabulary. Lets typed clients (and the consumer's own
integration tests) follow the contract without hand-translating the
Markdown spec.

## 5. Operational concerns

These came up during the pilot mount but aren't on the issue tracker
yet — they're more on the maintainer's roadmap than discrete features.

| Concern | Notes |
|---|---|
| **Pre-Alpha pinning** | `0.1.0a1` is correctly labeled Pre-Alpha. Document the API stability commitment (or lack thereof) per version segment so consumers know what to pin. |
| **Source maps in the wheel** | The shipped `.js.map` (740 KB) reveals SPA source structure to anyone with admin access. Defensible during alpha; consider stripping for the first stable release, or document a build flag. |
| **CSP guidance** | `SECURITY.md` mentions a CSP middleware sample is coming. For consumers running CSP today, surface the directives the SPA actually requires (`script-src 'self'`, `style-src 'self' 'unsafe-inline'`?) early. |
| **Security disclosure channel** | `SECURITY.md §1` still has `security@<TO-BE-CONFIGURED>`. Wire this up before stable; consumers won't file via public issue once they find something. |
| **Documented mount-prefix recipes** | The `_mount_from_request` heuristics handle the common cases, but a "mount at root" / "mount under a path that contains `api/v1/`" troubleshooting page would save a follow-up issue. |

## 6. Out of scope for this round

The pilot deliberately did not exercise the following — they're on the
consumer's roadmap but not blocking adoption:

- GIS / GeoDjango widgets.
- Rich-text editors via custom admin widgets (TinyMCE/Quill/CKEditor).
- Multi-database `using=` routing.
- Mobile / touch-first list editing.
- Internationalization (UI strings, date/number locales).
- Dark mode (covered separately in `../ux/principles.md`).

## 7. Acceptance signal

The library is "done" for this consumer when **every model the legacy
admin handles can be moved to the SPA without the consumer writing
backend or frontend glue** — driven purely by the existing
`ModelAdmin` declarations. The 12 issues above (`#54`–`#65`) are the
gap between that goal and `0.1.0a1`.

## 8. Tracker links

| # | Title | Theme |
|---|---|---|
| [#54](https://github.com/MartinCastroAlvarez/django-admin-react/issues/54) | Django inlines (Tabular / Stacked) | Read + Write |
| [#55](https://github.com/MartinCastroAlvarez/django-admin-react/issues/55) | ManyToMany read + write | Read + Write |
| [#56](https://github.com/MartinCastroAlvarez/django-admin-react/issues/56) | `list_filter` support | List UX |
| [#57](https://github.com/MartinCastroAlvarez/django-admin-react/issues/57) | `FileField` / `ImageField` | Read + Write |
| [#58](https://github.com/MartinCastroAlvarez/django-admin-react/issues/58) | `ModelAdmin.actions` + bulk | Write |
| [#59](https://github.com/MartinCastroAlvarez/django-admin-react/issues/59) | `autocomplete_fields` / `raw_id_fields` | Lookup ergonomics |
| [#60](https://github.com/MartinCastroAlvarez/django-admin-react/issues/60) | Field type vocabulary + extension hook | Read + Extensibility |
| [#61](https://github.com/MartinCastroAlvarez/django-admin-react/issues/61) | `list_editable` + bulk PATCH | Write |
| [#62](https://github.com/MartinCastroAlvarez/django-admin-react/issues/62) | `date_hierarchy` | List UX |
| [#63](https://github.com/MartinCastroAlvarez/django-admin-react/issues/63) | Session-expiry contract | SPA UX |
| [#64](https://github.com/MartinCastroAlvarez/django-admin-react/issues/64) | OpenAPI / schema endpoint | DX |
| [#65](https://github.com/MartinCastroAlvarez/django-admin-react/issues/65) | Frontend extension points | Extensibility |

— posted from a production Django integration pilot, 2026-05-26
