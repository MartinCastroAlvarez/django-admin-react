# @dar/form

The create/edit **write surface** — the metadata-driven widgets that turn
a `ModelAdmin` form schema (served by `@dar/data`) into editable controls.

## What lives here

- **`FieldInput`** — renders one form field from its `FieldDescriptor`:
  the right control per field type, validation/error display, and the
  readonly-field case (which falls back to the read-only renderer from
  `@dar/details`).
- **`AutocompleteInput`** — async typeahead for relation fields, backed
  by the autocomplete endpoint (via `@dar/data`'s `useApiClient`).
- **`InlineEditor`** — the inline formset editor (Django `inlines`):
  add / edit / delete related rows within the parent form.

## What does NOT belong here

- **Read-only display.** Rendering a *value* (not an editable control)
  is `@dar/details`' `FieldValueView`. `@dar/form` depends on
  `@dar/details` for the readonly-field case, never the reverse.
- **Page orchestration.** The create/edit *pages* (form state, submit,
  navigation) currently live in `@dar/web` and will move to a page
  package later (see issue #303). `@dar/form` is the widget toolkit those
  pages compose, not the pages themselves.
- **Network knowledge beyond `@dar/data`.** Per CLAUDE.md §7, never
  import `@dar/api` here — all data access goes through `@dar/data`.

## Dependencies

`@dar/form` → `@dar/details` (readonly display), `@dar/data` (schema +
client), `@dar/ui` (generic primitives). The dependency graph stays
acyclic: `@dar/web → { @dar/form, @dar/details }`, `@dar/form →
@dar/details → { @dar/data, … }`.

## Pointers

- Field/inline metadata shapes: `@dar/data` (`FieldDescriptor`,
  `InlineDescriptor`, `WriteValue`).
- Read-only value rendering: [`@dar/details`](../details/README.md).
- Generic controls (`Button`, `Input`): [`@dar/ui`](../ui/README.md).
