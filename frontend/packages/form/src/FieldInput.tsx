// FieldInput — one editable control for a FieldDescriptor.
//
// Maps the wire `type` vocabulary to an HTML input. Read-only fields
// and `unsupported` types render their value (not editable). FK fields
// render a <select> when the descriptor inlines `choices` (≤25 target
// rows), else a bare-pk text input with the current label shown (the
// autocomplete widget is a follow-up). The form value produced is a
// `WriteValue` (string | number | boolean | null) — FK sends the bare
// pk, per the wire contract §5.1.

import { useState } from 'react';
import { Plus } from 'lucide-react';

import type { FieldDescriptor, FieldValue, WriteValue } from '@dar/data';
import { FieldValueView } from '@dar/details';
import { Checkbox } from '@dar/ui';

import { AutocompleteInput } from './AutocompleteInput';
import { RelatedAddModal } from './RelatedAddModal';

interface FieldInputProps {
  name: string;
  field: FieldDescriptor;
  value: WriteValue;
  error: string[] | undefined;
  onChange: (value: WriteValue) => void;
}

const TEXTLIKE = new Set(['string', 'email', 'url', 'slug', 'uuid']);

function fkId(value: FieldValue): WriteValue {
  if (value && typeof value === 'object' && !Array.isArray(value) && 'id' in value) {
    return value.id;
  }
  return null;
}

export function FieldInput({ name, field, value, error, onChange }: FieldInputProps) {
  const id = `dar-input-${name}`;
  const base =
    'w-full rounded border px-2 py-1 text-sm ' +
    (error?.length ? 'border-red-400 focus:ring-red-500' : 'border-gray-300 focus:ring-gray-500');

  // Read-only / unsupported → show the value, no input.
  if (field.readonly || field.type === 'unsupported') {
    return (
      <Row id={id} field={field} error={error}>
        <div className="text-sm text-gray-700">
          <FieldValueView value={field.value} type={field.type} />
        </div>
      </Row>
    );
  }

  let control: React.ReactNode;

  if (field.widget === 'password') {
    // Field the admin routed through PasswordInput (#504). The backend
    // redacts the stored value (it ships `null`, matching Django's
    // `render_value=False`), so the box starts empty. Mask the input and
    // keep the browser from offering saved credentials for a secret field.
    control = (
      <input
        id={id}
        type="password"
        autoComplete="new-password"
        value={value == null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value)}
        className={base}
      />
    );
  } else if (field.type === 'boolean') {
    control = (
      <Checkbox id={id} checked={value === true} onChange={(e) => onChange(e.target.checked)} />
    );
  } else if (field.type === 'text') {
    control = (
      <textarea
        id={id}
        value={value == null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value)}
        rows={4}
        className={base}
      />
    );
  } else if (field.type === 'choice' || field.type === 'foreignkey') {
    control = (
      <ForeignKeyControl
        field={field}
        value={value}
        error={error}
        id={id}
        base={base}
        onChange={onChange}
      />
    );
  } else if (field.type === 'manytomany') {
    // ManyToMany write (#240). The backend accepts a list of pks
    // (form.save_m2m). When the target set is small the descriptor
    // inlines `choices` → render a checkbox multi-select producing a pk
    // array. Large M2M (filter_horizontal / autocomplete-backed, no
    // inlined choices) keeps a read-only view — a multi-picker widget is
    // a tracked follow-up on #240.
    const choices = field.choices ?? [];
    const selected = new Set((Array.isArray(value) ? value : []).map(String));
    if (choices.length > 0) {
      control = (
        <div className="max-h-48 space-y-1 overflow-y-auto rounded border border-gray-300 p-2">
          {choices.map((c) => {
            const key = String(c.value);
            return (
              <label key={key} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={selected.has(key)}
                  onChange={(e) => {
                    const next = new Set(selected);
                    if (e.target.checked) next.add(key);
                    else next.delete(key);
                    onChange(Array.from(next));
                  }}
                />
                {c.label}
              </label>
            );
          })}
        </div>
      );
    } else {
      control = (
        <div className="text-sm text-gray-700">
          <FieldValueView value={field.value} type={field.type} />
        </div>
      );
    }
  } else if (field.type === 'integer' || field.type === 'float' || field.type === 'decimal') {
    control = (
      <input
        id={id}
        type="number"
        step={field.type === 'integer' ? '1' : 'any'}
        value={value == null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        className={base}
      />
    );
  } else if (field.type === 'date') {
    control = (
      <input
        id={id}
        type="date"
        value={value == null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        className={base}
      />
    );
  } else if (field.type === 'datetime') {
    // The wire form is ISO 8601; <input type=datetime-local> wants
    // "YYYY-MM-DDTHH:MM". Trim the seconds/zone for the control, send
    // back what the user picked (Django parses it).
    const v = value == null ? '' : String(value).slice(0, 16);
    control = (
      <input
        id={id}
        type="datetime-local"
        value={v}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        className={base}
      />
    );
  } else if (field.type === 'time') {
    control = (
      <input
        id={id}
        type="time"
        value={value == null ? '' : String(value).slice(0, 8)}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        className={base}
      />
    );
  } else if (TEXTLIKE.has(field.type)) {
    control = (
      <input
        id={id}
        type={field.type === 'email' ? 'email' : field.type === 'url' ? 'url' : 'text'}
        value={value == null ? '' : String(value)}
        maxLength={field.max_length}
        onChange={(e) => onChange(e.target.value)}
        className={base}
      />
    );
  } else if (field.type === 'json') {
    // JSON editor (#242): a monospace textarea holding the serialized
    // value (the form seeds it as a pretty-printed string). The raw text
    // is sent as-is; Django's JSONField form field parses + validates it,
    // so malformed JSON surfaces as an ordinary field error — no parallel
    // client-side validation.
    control = (
      <textarea
        id={id}
        value={value == null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value)}
        rows={6}
        spellCheck={false}
        className={`${base} font-mono`}
      />
    );
  } else if (field.type === 'duration') {
    // DurationField editor (#242): a text input. Django's DurationField
    // form field parses the standard "[DD] [HH:[MM:]]ss[.uuuuuu]" form,
    // so we pass the string straight through and let it validate.
    control = (
      <input
        id={id}
        type="text"
        value={value == null ? '' : String(value)}
        placeholder="HH:MM:SS"
        onChange={(e) => onChange(e.target.value)}
        className={base}
      />
    );
  } else if (field.type === 'array') {
    // ArrayField editor (#242): a comma-delimited text input, mirroring
    // Django's SimpleArrayField widget. The form seeds it as the
    // comma-joined value; the raw string is sent as-is and SimpleArrayField
    // splits + coerces each element (reporting a bad element as a normal
    // field error). Values containing commas aren't supported — the same
    // limitation as Django's default admin widget.
    control = (
      <input
        id={id}
        type="text"
        value={value == null ? '' : String(value)}
        placeholder="comma,separated,values"
        onChange={(e) => onChange(e.target.value)}
        className={base}
      />
    );
  } else {
    // Fallback: render value read-only for any type without an editor.
    control = (
      <div className="text-sm text-gray-700">
        <FieldValueView value={field.value} type={field.type} />
      </div>
    );
  }

  return (
    <Row id={id} field={field} error={error}>
      {control}
    </Row>
  );
}

interface ForeignKeyControlProps {
  field: FieldDescriptor;
  value: WriteValue;
  error: string[] | undefined;
  id: string;
  base: string;
  onChange: (value: WriteValue) => void;
}

// FK / choice control with Django's related "+add" affordance (#383): a
// "+" next to a foreign-key field opens RelatedAddModal for the target
// model, then adds the created object to the options and selects it —
// without leaving the parent form (Django's RelatedFieldWidgetWrapper).
function ForeignKeyControl({ field, value, error, id, base, onChange }: ForeignKeyControlProps) {
  const [addOpen, setAddOpen] = useState(false);
  // The object just created via "+add", so it shows as selected even
  // though it isn't in the inlined choices / wasn't the initial value.
  const [added, setAdded] = useState<{ value: string | number; label: string } | null>(null);

  // "+add" only for a foreign key with a known, reachable target model;
  // plain choice enums and readonly fields get no "+".
  const canAdd = field.type === 'foreignkey' && field.to != null && !field.readonly;
  const onCreated = (created: { value: string | number; label: string }): void => {
    setAdded(created);
    onChange(created.value);
    setAddOpen(false);
  };

  const choices = field.choices ?? [];
  let control: React.ReactNode;
  if (choices.length > 0) {
    // Inlined choices (≤25 rows). Controlled by the form value so a change
    // — or a just-added object — shows; the added object is appended as an
    // extra option when not already listed.
    const withAdded =
      added && !choices.some((c) => String(c.value) === String(added.value))
        ? [...choices, { value: added.value, label: added.label }]
        : choices;
    control = (
      <select
        id={id}
        value={value == null ? '' : String(value)}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        className={base}
      >
        <option value="">{field.required ? '— select —' : '(none)'}</option>
        {withAdded.map((c) => (
          <option key={String(c.value)} value={String(c.value)}>
            {c.label}
          </option>
        ))}
      </select>
    );
  } else if (field.to) {
    // Large target table → typeahead. A just-added object isn't searchable
    // yet, so seed its label and remount (via key) so the picker shows it
    // as the current selection.
    const envelopeLabel =
      field.value && typeof field.value === 'object' && 'label' in field.value
        ? (field.value as { label: string }).label
        : undefined;
    control = (
      <AutocompleteInput
        key={added ? `added-${added.value}` : 'init'}
        to={field.to}
        value={value}
        initialLabel={added?.label ?? envelopeLabel}
        invalid={Boolean(error?.length)}
        onChange={onChange}
      />
    );
  } else {
    // FK with neither choices nor a `to` target — bare-pk fallback.
    const bare = fkId(field.value);
    control = (
      <input
        id={id}
        type="text"
        defaultValue={bare == null ? '' : String(bare)}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        placeholder="related object id"
        className={base}
      />
    );
  }

  if (!canAdd) return <>{control}</>;
  return (
    <div className="flex items-start gap-2">
      <div className="min-w-0 flex-1">{control}</div>
      <button
        type="button"
        onClick={() => setAddOpen(true)}
        aria-label={`Add ${field.label}`}
        title={`Add ${field.label}`}
        className="shrink-0 rounded-md border border-gray-300 p-1.5 text-gray-600 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <Plus className="h-4 w-4" aria-hidden />
      </button>
      {addOpen && field.to ? (
        <RelatedAddModal
          to={field.to}
          title={field.label}
          onCreated={onCreated}
          onClose={() => setAddOpen(false)}
        />
      ) : null}
    </div>
  );
}

interface RowProps {
  id: string;
  field: FieldDescriptor;
  error: string[] | undefined;
  children: React.ReactNode;
}

function Row({ id, field, error, children }: RowProps) {
  return (
    <div className="py-2 grid grid-cols-3 gap-4 text-sm items-start">
      <label htmlFor={id} className="text-gray-500 pt-1">
        {field.label}
        {field.required && !field.readonly ? <span className="text-red-500"> *</span> : null}
      </label>
      <div className="col-span-2">
        {children}
        {field.help_text ? <p className="mt-1 text-xs text-gray-400">{field.help_text}</p> : null}
        {error?.length ? <p className="mt-1 text-xs text-red-600">{error.join(' ')}</p> : null}
      </div>
    </div>
  );
}
