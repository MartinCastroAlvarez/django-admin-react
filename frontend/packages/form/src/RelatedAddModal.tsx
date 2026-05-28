// RelatedAddModal — Django's related "+add" popup (#383).
//
// Opened from a foreign-key field's "+" button: loads the *target*
// model's add-form schema, renders its fields with the same FieldInput
// the create page uses, and POSTs via createObject. On success it hands
// the new object back as `{ value, label }` so the FK field can select it
// immediately — matching Django's RelatedFieldWidgetWrapper, which adds
// the new object and selects it without leaving the parent form.
//
// Self-contained (its own schema fetch + state) so it doesn't depend on
// the page-level create flow. Inlines / fieldset grouping are out of
// scope for this popup — it renders the flat visible field set, which is
// what the related add form needs in practice.

import { useEffect, useMemo, useState } from 'react';

import {
  ApiError,
  createObject,
  useApiClient,
  type AddFormResponse,
  type FieldDescriptor,
  type WriteValue,
} from '@dar/data';
import { Button, Modal } from '@dar/ui';

import { FieldInput } from './FieldInput';

export interface RelatedAddModalProps {
  /** The FK target model (`field.to`). */
  to: { app_label: string; model_name: string };
  /** Human label for the modal title (e.g. the FK field's label). */
  title?: string;
  /** Called with the created object so the opener can select it. */
  onCreated: (created: { value: string | number; label: string }) => void;
  onClose: () => void;
}

// Seed a write value from a field's default, mirroring the create page:
// scalars pass through; JSON/array seed their string form; objects (FK
// envelopes) and unknown defaults start empty.
function seedValue(field: FieldDescriptor): WriteValue {
  const v = field.value;
  if (field.type === 'manytomany') return [];
  if (field.type === 'json') return v == null ? null : JSON.stringify(v, null, 2);
  if (field.type === 'array') return Array.isArray(v) ? v.join(',') : null;
  if (field.type === 'range') return rangeToPair(v);
  return v != null && typeof v !== 'object' ? (v as WriteValue) : null;
}

// RangeField (#242): unwrap the read envelope
// `{subtype, value: {lower, upper, bounds}}` into the `[lower, upper]`
// array shape the backend `_range_endpoints` accepts (#533). An empty
// side stays empty (= unbounded); a missing envelope → empty pair so a
// new object starts with two empty inputs instead of `null`.
function rangeToPair(v: unknown): WriteValue {
  if (v && typeof v === 'object' && 'value' in v) {
    const inner = (v as { value?: unknown }).value;
    if (inner && typeof inner === 'object') {
      const lower = (inner as { lower?: unknown }).lower;
      const upper = (inner as { upper?: unknown }).upper;
      return [lower == null ? '' : String(lower), upper == null ? '' : String(upper)];
    }
  }
  return ['', ''];
}

export function RelatedAddModal({ to, title, onCreated, onClose }: RelatedAddModalProps) {
  const client = useApiClient();
  const [schema, setSchema] = useState<AddFormResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [values, setValues] = useState<Record<string, WriteValue>>({});
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [nonFieldError, setNonFieldError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let live = true;
    setSchema(null);
    setLoadError(null);
    client
      .addForm(to.app_label, to.model_name)
      .then((res) => {
        if (!live) return;
        setSchema(res);
        const init: Record<string, WriteValue> = {};
        for (const [name, field] of Object.entries(res.fields)) {
          if (!field.readonly) init[name] = seedValue(field);
        }
        setValues(init);
      })
      .catch((err: unknown) => {
        if (live) setLoadError(err instanceof Error ? err.message : 'Could not load the form.');
      });
    return () => {
      live = false;
    };
  }, [client, to.app_label, to.model_name]);

  // Visible (non-readonly) fields, in the schema's declared order.
  const visibleFields = useMemo(
    () => Object.entries(schema?.fields ?? {}).filter(([, f]) => !f.readonly),
    [schema],
  );

  async function submit(): Promise<void> {
    if (!schema || saving) return;
    setSaving(true);
    setErrors({});
    setNonFieldError(null);
    try {
      const res = await createObject({
        client,
        appLabel: to.app_label,
        modelName: to.model_name,
        payload: values,
      });
      onCreated({ value: res.pk, label: res.label });
    } catch (err) {
      if (err instanceof ApiError && err.envelope?.error?.fields) {
        const fields = err.envelope.error.fields;
        const { __all__: nonField, ...rest } = fields;
        setErrors(rest);
        if (nonField?.length) setNonFieldError(nonField.join(' '));
        else if (Object.keys(rest).length === 0) {
          setNonFieldError(err.envelope.error.message ?? 'Could not save.');
        }
      } else {
        setNonFieldError(err instanceof Error ? err.message : 'Could not save.');
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={title ? `Add ${title}` : 'Add'} onClose={onClose}>
      {loadError ? (
        <p className="text-sm text-red-600">{loadError}</p>
      ) : !schema ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
          className="space-y-4"
        >
          {nonFieldError ? (
            <p className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
              {nonFieldError}
            </p>
          ) : null}
          <div className="space-y-3">
            {visibleFields.map(([name, field]) => (
              <FieldInput
                key={name}
                name={name}
                field={field}
                value={values[name] ?? null}
                error={errors[name]}
                onChange={(v) => setValues((prev) => ({ ...prev, [name]: v }))}
              />
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
