// FieldInput — one editable control for a FieldDescriptor.
//
// Maps the wire `type` vocabulary to an HTML input. Read-only fields
// and `unsupported` types render their value (not editable). FK fields
// render a <select> when the descriptor inlines `choices` (≤25 target
// rows), else a bare-pk text input with the current label shown (the
// autocomplete widget is a follow-up). The form value produced is a
// `WriteValue` (string | number | boolean | null) — FK sends the bare
// pk, per the wire contract §5.1.

import type { FieldDescriptor, FieldValue, WriteValue } from '@dar/data';
import { FieldValueView } from '@dar/details';
import { Checkbox } from '@dar/ui';

import { AutocompleteInput } from './AutocompleteInput';

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

  // Masked field (#504): a CharField rendered with `PasswordInput` via
  // `formfield_overrides`. Mask the input and — mirroring Django's
  // `PasswordInput(render_value=False)` — do NOT seed the stored value
  // into the DOM. Uncontrolled (`defaultValue=""`) so the secret never
  // reaches devtools; we send only what the user types.
  if (field.widget === 'password') {
    return (
      <Row id={id} field={field} error={error}>
        <input
          id={id}
          type="password"
          autoComplete="new-password"
          defaultValue=""
          maxLength={field.max_length}
          onChange={(e) => onChange(e.target.value)}
          className={base}
        />
      </Row>
    );
  }

  let control: React.ReactNode;

  if (field.type === 'boolean') {
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
    const choices = field.choices ?? [];
    if (choices.length > 0) {
      const current = field.type === 'foreignkey' ? fkId(field.value) : value;
      control = (
        <select
          id={id}
          value={current == null ? '' : String(current)}
          onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
          className={base}
        >
          <option value="">{field.required ? '— select —' : '(none)'}</option>
          {choices.map((c) => (
            <option key={String(c.value)} value={String(c.value)}>
              {c.label}
            </option>
          ))}
        </select>
      );
    } else if (field.to) {
      // FK with no inlined choices (large target table) — typeahead
      // against the target model's autocomplete endpoint.
      const currentLabel =
        field.value && typeof field.value === 'object' && 'label' in field.value
          ? (field.value as { label: string }).label
          : undefined;
      control = (
        <AutocompleteInput
          to={field.to}
          value={value}
          initialLabel={currentLabel}
          invalid={Boolean(error?.length)}
          onChange={onChange}
        />
      );
    } else {
      // FK with neither choices nor a `to` target — bare-pk fallback.
      const current = fkId(field.value);
      control = (
        <input
          id={id}
          type="text"
          defaultValue={current == null ? '' : String(current)}
          onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
          placeholder="related object id"
          className={base}
        />
      );
    }
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
