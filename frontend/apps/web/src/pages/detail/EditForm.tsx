import { useCallback, useRef, useState } from 'react';

import {
  ApiError,
  type DetailResponse,
  type InlineWriteItem,
  type InlineWritePayload,
  type WriteValue,
} from '@dar/data';
import { Button, Card } from '@dar/ui';
import { FieldInput, InlineEditor } from '@dar/form';

import { useUnsavedGuard } from '../../useUnsavedGuard';

/**
 * Which save-flow button was pressed (Django parity, #154). The parent
 * routes navigation per action; the form only builds + submits.
 */
export type SaveAction = 'save' | 'continue' | 'addAnother' | 'saveAsNew';

export interface EditFormProps {
  data: DetailResponse;
  onCancel: () => void;
  onSave: (payload: import('@dar/data').UpdatePayload, action: SaveAction) => Promise<void>;
}

function initialValueFor(field: DetailResponse['fields'][string]): WriteValue {
  const v = field.value;
  if (v === null || v === undefined) return null;
  if (field.type === 'json') {
    // JSON editor (#242): seed the textarea with the pretty-printed value
    // (a string) so an untouched field round-trips its existing JSON
    // intact instead of being wiped. Checked before the array branch so
    // a JSON array isn't mistaken for an M2M id list.
    return JSON.stringify(v, null, 2);
  }
  if (field.type === 'array') {
    // ArrayField editor (#242): seed the comma-joined value (string),
    // matching Django's SimpleArrayField widget. Checked before the M2M
    // array branch so the scalar list isn't mapped to {id} envelopes.
    return Array.isArray(v) ? v.join(',') : null;
  }
  if (field.type === 'range') {
    // RangeField editor (#242): unwrap the read envelope
    // `{subtype, value: {lower, upper, bounds}}` into the `[lower, upper]`
    // array shape `_range_endpoints` accepts (#533). Checked before the
    // generic object branch so the envelope isn't mistaken for an FK.
    if (v && typeof v === 'object' && 'value' in v) {
      const inner = (v as { value?: unknown }).value;
      if (inner && typeof inner === 'object') {
        const lower = (inner as { lower?: unknown }).lower;
        const upper = (inner as { upper?: unknown }).upper;
        return [
          lower == null ? '' : String(lower),
          upper == null ? '' : String(upper),
        ];
      }
    }
    return ['', ''];
  }
  if (Array.isArray(v)) {
    // M2M (#240): [{id,label}, ...] → [id, ...] (bare pks for the write).
    return v.map((item) =>
      item && typeof item === 'object' && 'id' in item ? item.id : (item as string | number),
    );
  }
  if (typeof v === 'object') {
    // FK envelope {id,label} → id; html → leave null (not edited here).
    if ('id' in v) return v.id;
    return null;
  }
  return v;
}

/**
 * Edit-mode form for a detail object. Seeds each editable field from the
 * read payload, PATCHes via `onSave`, and surfaces field-level + non-field
 * validation errors. Renders the save-flow buttons `save_options` allows
 * (#154) and collects editable inline blocks for the write (#54).
 */
export function EditForm({ data, onCancel, onSave }: EditFormProps) {
  const [values, setValues] = useState<Record<string, WriteValue>>(() => {
    const init: Record<string, WriteValue> = {};
    for (const [name, field] of Object.entries(data.fields)) {
      if (!field.readonly) init[name] = initialValueFor(field);
    }
    return init;
  });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [nonFieldError, setNonFieldError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // Inline write items collected from each InlineEditor, keyed by name.
  const [inlineItems, setInlineItems] = useState<Record<string, InlineWriteItem[]>>({});

  // Unsaved-changes guard (#290): snapshot the initial values once, then
  // warn on tab-close/reload while the form differs from that snapshot.
  const initialJsonRef = useRef<string | null>(null);
  if (initialJsonRef.current === null) initialJsonRef.current = JSON.stringify(values);
  const dirty = JSON.stringify(values) !== initialJsonRef.current;
  useUnsavedGuard(dirty && !saving);

  // Stable so InlineEditor's effect doesn't re-fire every render.
  const handleInlineItems = useCallback((name: string, items: InlineWriteItem[]) => {
    setInlineItems((prev) => ({ ...prev, [name]: items }));
  }, []);

  // Inlines the user can actually modify (per-inline permission flags).
  const editableInlines = (data.inlines ?? []).filter(
    (inline) => inline.can_add || inline.can_change || inline.can_delete,
  );

  async function runSave(action: SaveAction) {
    setSaving(true);
    setErrors({});
    setNonFieldError(null);
    // Build the PATCH body: parent field values + any non-empty inline
    // blocks (api-contract §5.2.1). Empty inline blocks are omitted so
    // an untouched inline never posts.
    const payload: import('@dar/data').UpdatePayload = { ...values };
    const inlines: InlineWritePayload = {};
    for (const [name, items] of Object.entries(inlineItems)) {
      if (items.length > 0) inlines[name] = { items };
    }
    if (Object.keys(inlines).length > 0) payload.inlines = inlines;
    try {
      await onSave(payload, action);
      // Save succeeded — rebase the dirty snapshot so "Save and continue
      // editing" (form stays mounted) doesn't keep warning about edits
      // that are now persisted.
      initialJsonRef.current = JSON.stringify(values);
    } catch (err) {
      if (err instanceof ApiError && err.envelope?.error) {
        // Non-field errors (a ModelForm.clean() / __all__ cross-field
        // rule) arrive under the empty-string key (#381). Surface them
        // as the form-level banner and render the named field errors
        // inline — both can show at once.
        const { ['']: nonField, ...namedErrors } = err.envelope.error.fields ?? {};
        setErrors(namedErrors);
        const banner =
          nonField?.join(' ') ||
          (Object.keys(namedErrors).length === 0 ? err.envelope.error.message : '');
        setNonFieldError(banner || null);
      } else {
        setNonFieldError(err instanceof Error ? err.message : 'Save failed.');
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await runSave('save');
  }

  const so = data.save_options;

  // Save-flow buttons (#154) — render only what `save_options` allows;
  // default to a plain Save for older backends. Built as a function so it
  // can be rendered both at the top (when `save_on_top`, #251) and bottom.
  const renderSaveActions = () => (
    <div className="flex flex-wrap gap-2">
      {(so?.show_save ?? true) && (
        <Button type="submit" variant="primary" disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </Button>
      )}
      {so?.show_save_and_continue && (
        <Button
          type="button"
          variant="secondary"
          disabled={saving}
          onClick={() => void runSave('continue')}
        >
          Save and continue editing
        </Button>
      )}
      {so?.show_save_and_add_another && (
        <Button
          type="button"
          variant="secondary"
          disabled={saving}
          onClick={() => void runSave('addAnother')}
        >
          Save and add another
        </Button>
      )}
      {so?.show_save_as_new && (
        <Button
          type="button"
          variant="secondary"
          disabled={saving}
          onClick={() => void runSave('saveAsNew')}
        >
          Save as new
        </Button>
      )}
      <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
        Cancel
      </Button>
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {nonFieldError && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {nonFieldError}
        </div>
      )}
      {so?.save_on_top && renderSaveActions()}
      {data.fieldsets.map((fieldset, idx) => {
        // Edit mode shows only fields the operator can actually change:
        // drop readonly fields from each row, then drop now-empty rows.
        // A fieldset left with nothing editable is hidden entirely (no
        // empty card).
        const editableRows = (fieldset.field_rows ?? fieldset.fields.map((f) => [f]))
          .map((row) => row.filter((name) => data.fields[name] && !data.fields[name]?.readonly))
          .filter((row) => row.length > 0);
        if (editableRows.length === 0) return null;

        const renderInput = (name: string) => {
          const field = data.fields[name];
          if (!field) return null;
          return (
            <FieldInput
              key={name}
              name={name}
              field={field}
              value={values[name] ?? null}
              error={errors[name]}
              onChange={(v) => setValues((prev) => ({ ...prev, [name]: v }))}
            />
          );
        };

        return (
          <Card key={`efs-${idx}-${fieldset.title ?? 'default'}`} title={fieldset.title ?? undefined}>
            <div className="divide-y divide-gray-100">
              {editableRows.map((row, ri) => {
                if (row.length === 1) return renderInput(row[0] as string);
                // Multi-field row (#382): inputs side by side.
                return (
                  <div
                    key={ri}
                    className="grid gap-4 py-1"
                    style={{ gridTemplateColumns: `repeat(${row.length}, minmax(0, 1fr))` }}
                  >
                    {row.map((name) => renderInput(name))}
                  </div>
                );
              })}
            </div>
          </Card>
        );
      })}

      {/* Editable inlines (#54 write half) — typed inputs per child row,
          add/remove, submitted via the PATCH `inlines` block. */}
      {editableInlines.map((inline) => (
        <Card key={`inline-${inline.name}`} title={inline.label}>
          <InlineEditor inline={inline} onItems={handleInlineItems} />
          {errors[`inlines.${inline.name}`]?.map((msg, i) => (
            <p key={i} className="mt-2 text-xs text-red-600">
              {msg}
            </p>
          ))}
        </Card>
      ))}

      {renderSaveActions()}
    </form>
  );
}
