// adaptFormSpec — map a form-spec payload onto the detail-payload shape so
// the existing EditForm / FieldInput render it unchanged (#659).
//
// The form-spec endpoint (rest-api 1.4.0+, #59) is the source of truth for
// the change/add form: it resolves the ModelAdmin layer (request-aware
// `get_form` / `get_fieldsets` / `get_readonly_fields`, `formfield_overrides`,
// custom Form classes) the model serializer can't see. Rather than rebuild
// every control, we translate each `FormSpecField` into the `FieldDescriptor`
// the battle-tested FieldInput already renders — the backend reuses the
// detail serializer for `initial`, so the value shapes line up exactly.

import type {
  DetailResponse,
  FieldDescriptor,
  FormSpecField,
  FormSpecResponse,
  WidgetKind,
  WidgetHint,
} from '@dar/data';

// The closed `widget.kind` enum → the SPA's `WidgetHint` controls (#664).
//
// EVERY one of the 23 declared `WidgetKind` values is mapped explicitly so
// no kind silently degrades to a wrong control:
//   • `undefined` — the control `FieldType` already implies is faithful
//     (e.g. `text` → text input, `select` → <select>, `date` → date input,
//     `datetime` → datetime-local, `time` → time input, `checkbox` →
//     boolean checkbox, `number` → number input, `email`/`url` → typed
//     inputs). Listed here on purpose so adding a kind is a compile error
//     until it's classified (the test asserts the record is exhaustive).
//   • a real hint — a kind that needs a control `FieldType` would NOT pick
//     (hidden, split-datetime, the multi-selects, autocomplete, file, …).
// There is no implicit fallback: an unmapped kind would be a `undefined`
// type error, and a kind we can't render faithfully maps to the explicit,
// operator-visible `unsupported_widget` tracked fallback in FieldInput.
const KIND_TO_HINT: Record<WidgetKind, WidgetHint | undefined> = {
  // Kinds whose FieldType-derived control is already faithful.
  text: undefined,
  textarea: undefined,
  number: undefined,
  email: undefined,
  url: undefined,
  checkbox: undefined,
  select: undefined,
  date: undefined,
  datetime: undefined,
  time: undefined,
  // Security / parity hints that were already wired.
  password: 'password',
  radio: 'radio',
  'raw-id': 'raw_id',
  // form-spec collapses filter_horizontal/vertical to a single `shuttle`
  // kind; orientation isn't carried, so default to horizontal (the
  // ShuttleSelect supports both and the difference is purely visual).
  shuttle: 'shuttle_h',
  custom: 'custom',
  // Kinds that need a control FieldType alone would render WRONGLY (#664).
  hidden: 'hidden',
  'split-datetime': 'split_datetime',
  'select-date': 'select_date',
  'checkbox-multiple': 'checkbox_multiple',
  'select-multiple': 'select_multiple',
  autocomplete: 'autocomplete',
  'autocomplete-multiple': 'autocomplete_multiple',
  file: 'file',
};

function maxLengthFrom(field: FormSpecField): number | undefined {
  if (typeof field.max_length === 'number') return field.max_length;
  const attr = field.widget.attrs['maxlength'];
  return typeof attr === 'number' ? attr : undefined;
}

/** Translate one form-spec field into a detail-style FieldDescriptor.
 *
 * Optional keys are added only when present — the project's
 * `exactOptionalPropertyTypes` forbids assigning `undefined` to an
 * optional prop. */
export function formSpecFieldToDescriptor(field: FormSpecField): FieldDescriptor {
  const descriptor: FieldDescriptor = {
    type: field.type,
    label: field.label,
    required: field.required,
    readonly: field.readonly,
    help_text: field.help_text,
    // `initial` reuses the detail serializer's value shape verbatim
    // (FK {id,label}, M2M [{id,label}], redacted password → null), so
    // EditForm's `initialValueFor` derives the write value unchanged.
    value: field.initial,
  };
  if (field.choices) descriptor.choices = field.choices;
  if (field.to) descriptor.to = field.to;
  const maxLength = maxLengthFrom(field);
  if (maxLength !== undefined) descriptor.max_length = maxLength;
  if (field.decimal_places !== undefined) descriptor.decimal_places = field.decimal_places;
  const hint = KIND_TO_HINT[field.widget.kind];
  if (hint !== undefined) descriptor.widget = hint;
  if (field.widget.widget_class !== undefined) descriptor.widget_class = field.widget.widget_class;
  return descriptor;
}

/**
 * Build a DetailResponse-shaped object whose `fields` + `fieldsets` come
 * from the form spec while inlines / save_options / permissions / label
 * stay from the live detail payload. Lets the existing EditForm render the
 * ModelAdmin-resolved form with no other change.
 */
export function detailFromFormSpec(
  detail: DetailResponse,
  spec: FormSpecResponse,
): DetailResponse {
  const fields: Record<string, FieldDescriptor> = {};
  for (const [name, field] of Object.entries(spec.fields)) {
    fields[name] = formSpecFieldToDescriptor(field);
  }
  return { ...detail, fields, fieldsets: spec.fieldsets };
}
