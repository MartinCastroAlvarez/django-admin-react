# @dar/details

The read / display surface for a single object.

## What lives here

- **`FieldValueView`** — renders one wire-shape field/cell *value* for
  display (not an editable control): booleans as Django's check/X icons,
  foreign keys as navigable links, files as download links, the backend's
  safe-HTML envelope as markup, everything else as escaped text. Shared by
  the list (`@dar/web` `ListPage`), the detail page, and `@dar/form` (for
  readonly fields).

The detail-page *orchestration* (layout from `fieldsets`, history,
delete) still lives in `@dar/web` and is slated to move here — see issue
[#303](https://github.com/MartinCastroAlvarez/django-admin-react/issues/303).

## What does NOT belong here

- **Editable controls.** Rendering an *input* is `@dar/form`'s job
  (`FieldInput`, `AutocompleteInput`, `InlineEditor`). `@dar/details` is
  the read side; `@dar/form` depends on it, never the reverse.
- **Direct network access.** Per CLAUDE.md §7 / `ARCHITECTURE.md` §5.2a,
  never import `@dar/api`. All data access goes through `@dar/data`.

## Pointers

- Field-value shapes + type guards (`isHtmlValue`, `isForeignKeyValue`,
  `isFileValue`, `renderValue`): `@dar/data`.
- The write surface: [`@dar/form`](../form/README.md).
- The safe-HTML trust boundary: `SECURITY.md` + #172.
