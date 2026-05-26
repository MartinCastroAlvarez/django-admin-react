# Consumer feedback — production-Django pilot (2026-05-26)

A real Django + React integration team did a pilot of `0.1.0a1`,
mounting the SPA at a second admin path alongside their existing
legacy admin. The library installs cleanly, the registry / list /
detail / create / update / destroy endpoints behave as the docs
promise, and the security posture (CSRF on, no `@csrf_exempt`, opaque
404 bodies, `Cache-Control: no-store` on every response,
sensitive-name denylist, `ModelAdmin` as the single source of truth)
held up to a full source audit. **Nothing security-shaped is blocking
adoption.**

What *is* blocking adoption past the simplest leaf models is a set of
standard `django.contrib.admin` features that aren't wired up yet.
The team filed twelve generic, anonymized issues capturing each gap
and a single requirements doc summarizing them.

## Artifacts

- Full requirements doc:
  [`docs/consumer/requirements-laminr-pilot-2026-05-26.md`](../docs/consumer/requirements-laminr-pilot-2026-05-26.md)

- GitHub issues filed (all `enhancement`):

  | Theme | Issues |
  |---|---|
  | Read + Write | [#54 inlines](https://github.com/MartinCastroAlvarez/django-admin-react/issues/54), [#55 M2M](https://github.com/MartinCastroAlvarez/django-admin-react/issues/55), [#57 files](https://github.com/MartinCastroAlvarez/django-admin-react/issues/57), [#60 field-type vocabulary](https://github.com/MartinCastroAlvarez/django-admin-react/issues/60) |
  | List UX | [#56 list_filter](https://github.com/MartinCastroAlvarez/django-admin-react/issues/56), [#62 date_hierarchy](https://github.com/MartinCastroAlvarez/django-admin-react/issues/62) |
  | Write | [#58 admin actions](https://github.com/MartinCastroAlvarez/django-admin-react/issues/58), [#61 list_editable + bulk PATCH](https://github.com/MartinCastroAlvarez/django-admin-react/issues/61) |
  | Lookup ergonomics | [#59 autocomplete / raw_id_fields](https://github.com/MartinCastroAlvarez/django-admin-react/issues/59) |
  | SPA UX | [#63 session-expiry contract](https://github.com/MartinCastroAlvarez/django-admin-react/issues/63) |
  | DX | [#64 OpenAPI / schema endpoint](https://github.com/MartinCastroAlvarez/django-admin-react/issues/64) |
  | Extensibility | [#65 frontend extension points](https://github.com/MartinCastroAlvarez/django-admin-react/issues/65) |

## Headlines

- **No security findings.** The audit was clean — staff+CSRF gate,
  no outbound network calls, no `eval`/`exec` in source, no telemetry
  in the bundle. The only "watch this" notes are operational
  (security@ placeholder in `SECURITY.md §1`, source maps in the
  shipped wheel) — already in the requirements doc §5.
- **The library is safe to ship alongside the legacy admin today**,
  on a second path, behind a settings flag — even at `0.1.0a1`.
- **It is not yet ready to replace the legacy admin** for the
  consumer's heavier models. Inlines, `list_filter`, admin actions,
  M2M, file uploads, and `date_hierarchy` are the big rocks. None of
  them are "research projects" — they're well-trodden Django primitives
  with clear acceptance signals in the issues.
- **`ModelAdmin` as the single source of truth is the right call** and
  the consumer wants the maintainer to defend that line. The
  extension points asked for in `#60` and `#65` are scoped to *plug
  into* that contract, not work around it.

## Suggested triage

The consumer would prioritize from a real-adoption standpoint as:

1. `#54` inlines + `#55` M2M — every non-trivial app has these.
2. `#56` `list_filter` + `#62` `date_hierarchy` — every operator
   workflow needs filter-by-X-then-narrow-by-date.
3. `#57` files + `#58` admin actions — heavy admin lever; without
   them the SPA is "browse-only" for many models.
4. `#59` autocomplete — performance/UX gate for any model with a
   high-cardinality FK.
5. `#60` field types + `#61` `list_editable` + `#63` session expiry
   + `#64` schema + `#65` extensibility — quality, contract clarity,
   and "I shouldn't have to fork to add one widget."

The consumer is happy to pair with the maintainer on any of these
once they're picked up.

— posted from a production Django integration pilot
