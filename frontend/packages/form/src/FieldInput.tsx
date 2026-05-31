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
import { Checkbox, lookupFieldWidget, t } from '@dar/ui';

import { AutocompleteInput } from './AutocompleteInput';
import { CustomWidgetMount } from './CustomWidgetMount';
import { RelatedAddModal } from './RelatedAddModal';
import { ShuttleSelect } from './ShuttleSelect';

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
  } else if (field.widget === 'custom' && field.widget_class) {
    // Custom widget plugin protocol (#625). The API (1.3.0+) marks
    // any field whose bound form widget class lives outside
    // ``django.*`` with ``widget: "custom"`` + the widget's dotted
    // Python path. Consumers register a vanilla mount fn for that
    // class via ``registerFieldWidget(class, {mount})``; the SPA's
    // ``CustomWidgetMount`` adapter bridges React → the mount fn's
    // imperative DOM world.
    //
    // If no registration matches, render the default control for the
    // field's type with a small inline note so the operator isn't
    // stuck — they can still type something into the field; the
    // consumer's missing widget is a deployment gap, not a hard
    // block. The note links to the legacy admin which has the real
    // widget rendered server-side.
    const widgetSpec = lookupFieldWidget(field.widget_class);
    if (widgetSpec) {
      control = (
        <CustomWidgetMount
          spec={widgetSpec}
          widgetClass={field.widget_class}
          value={value}
          onChange={onChange}
          error={error}
        />
      );
    } else {
      control = (
        <div className="space-y-1">
          <input
            id={id}
            type="text"
            value={value == null ? '' : String(value)}
            onChange={(e) => onChange(e.target.value)}
            className={base}
          />
          <p className="text-xs text-amber-700">
            {t('Custom widget')} <code className="font-mono">{field.widget_class}</code>{' '}
            {t('is not registered; using the default text input.')}
          </p>
        </div>
      );
    }
  } else if (field.widget === 'raw_id' && field.type === 'foreignkey') {
    // raw_id_fields (#626 / #251). The consumer explicitly OPTED OUT
    // of an autocomplete picker — typically because the FK target has
    // millions of rows and `get_search_results` is too expensive.
    // Match Django's HTML admin: a bare pk text input, plus a small
    // "lookup" link that opens the FK target's changelist in a new
    // tab so the operator can find the pk by sight. No autocomplete
    // request fires. The wire ships `field.to = {app_label, model_name}`
    // when the FK target is admin-registered (`#184` parity); when it
    // isn't, we render the input only.
    //
    // M2M + `raw_id` is intentionally NOT handled here; falls through
    // to the existing M2M branch (CSV pk list is a separate follow-up).
    const target = field.to;
    control = (
      <div className="flex items-center gap-2">
        <input
          id={id}
          type="text"
          inputMode="numeric"
          value={value == null ? '' : String(value)}
          onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
          className={base}
        />
        {target && (
          <a
            // Same-window? No — popup is the legacy admin's contract.
            // Open the changelist in a new tab; the operator copies
            // the pk back into the input.
            href={`../../${target.app_label}/${target.model_name}/`}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
            aria-label="Look up related object in a new tab"
          >
            Lookup ↗
          </a>
        )}
      </div>
    );
  } else if (field.widget === 'radio' && field.type === 'choice' && field.choices) {
    // radio_fields (#626 / #251). The consumer explicitly chose inline
    // radio buttons over the default `<select>` — typically because the
    // option set is small (2-5) and a radio bank is faster to scan than
    // a click + dropdown. The wire ships the choices list verbatim;
    // render one labeled radio per option. Falls through to the choice
    // branch when `field.choices` is empty (defence — choice fields
    // should always carry choices, but the type allows undefined).
    const radioValue = value == null ? '' : String(value);
    control = (
      <div role="radiogroup" aria-labelledby={`${id}-label`} className="flex flex-wrap gap-x-4 gap-y-2">
        {field.choices.map((c) => {
          const key = String(c.value);
          return (
            <label key={key} className="flex items-center gap-1.5 text-sm">
              <input
                type="radio"
                name={id}
                value={key}
                checked={radioValue === key}
                onChange={() => onChange(c.value)}
                className="h-4 w-4 text-gray-700 focus:ring-gray-500"
              />
              {c.label}
            </label>
          );
        })}
      </div>
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
  } else if (
    field.type === 'manytomany' &&
    (field.widget === 'shuttle_h' || field.widget === 'shuttle_v') &&
    field.choices &&
    field.choices.length > 0
  ) {
    // filter_horizontal / filter_vertical (#627). The admin opted into
    // Django's two-pane "available / chosen" shuttle widget — the API
    // emits `widget: "shuttle_h"` or `"shuttle_v"` (api 1.2.0+) and
    // we render a real shuttle with per-pane search, selection-order
    // preservation, and "Choose all / Remove all" bulk actions.
    // Scales well past the ~50-option ceiling where the default
    // checkbox list breaks down.
    control = (
      <ShuttleSelect
        id={id}
        choices={field.choices}
        value={value}
        orientation={field.widget === 'shuttle_v' ? 'v' : 'h'}
        label={field.label}
        onChange={(next) => onChange(next as unknown as WriteValue)}
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
  } else if (field.type === 'range') {
    // RangeField editor (#242, paired with the write-half in #533). Two
    // text inputs (lower / upper) wired to the `[lower, upper]` array
    // shape `_range_endpoints` accepts. Subtype-aware formatting is the
    // user's job: Django's `MultiValueField` sub-fields validate each
    // side per its subtype (date / datetime / int / decimal) and surface
    // a bad value as a normal field error — same contract as the json /
    // duration / array editors. An empty side = unbounded. The form
    // seeds the pair from the read envelope `{subtype, value: {lower,
    // upper, bounds}}`.
    const pair: [string, string] =
      Array.isArray(value) && value.length === 2
        ? [String(value[0] ?? ''), String(value[1] ?? '')]
        : ['', ''];
    control = (
      <div className="flex items-center gap-2">
        <input
          id={id}
          type="text"
          value={pair[0]}
          placeholder="lower"
          aria-label={`${field.label} lower bound`}
          onChange={(e) => onChange([e.target.value, pair[1]])}
          className={base}
        />
        <span aria-hidden className="text-gray-400">
          –
        </span>
        <input
          type="text"
          value={pair[1]}
          placeholder="upper"
          aria-label={`${field.label} upper bound`}
          onChange={(e) => onChange([pair[0], e.target.value])}
          className={base}
        />
      </div>
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
