# @dar/details — generic detail / create / update / delete forms

Reads the field metadata from `GET /api/v1/{app}/{model}/{pk}/` (or the
"new object" equivalent for create) and renders a form. Submits via
**`@dar/data`** mutations (which debounce and reconcile before calling
`@dar/api`).

## Rules

- **`@dar/data` is the only data source.** Never import `@dar/api`
  directly. See [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §5.2a.
- The form layout follows the API's `fieldsets`.
- Field widgets are picked by `type` from the closed v1 vocabulary
  (`string`, `integer`, `boolean`, `foreignkey`, ...). See
  `docs/api-contract.md` §4.
- Readonly fields render as static text.
- `unsupported` fields render as static labels (M2M in v1).
- Submit button is hidden if `permissions.change`/`add` is false.
