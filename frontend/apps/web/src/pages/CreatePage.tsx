// CreatePage — add a new object.
//
// Fetches the create-form schema from GET <app>/<model>/add/ (same
// field/fieldset shape as detail, for an unsaved object), renders the
// shared FieldInput form, and POSTs via createObject. Field-level
// validation errors come back in the envelope and render next to each
// input. On success, navigates to the new object's detail page.

import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  ApiError,
  createObject,
  useApiClient,
  type AddFormResponse,
  type WriteValue,
} from '@dar/data';
import { Breadcrumb, Button, Card, EmptyState } from '@dar/ui';
import { FieldInput } from '@dar/form';

import { RecordSkeleton } from '../components/RecordSkeleton';
import { slugify } from '../slugify';
import { useModelMeta } from '../useModelMeta';
import { useToast } from '../toast';
import { useUnsavedGuard } from '../useUnsavedGuard';
import { carryPreservedFilters, listPathWithPreservedFilters } from '../changelistFilters';

export function CreatePage() {
  const params = useParams<{ appLabel: string; modelName: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const client = useApiClient();
  const navigate = useNavigate();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  // Where "back to the list" goes — restoring the operator's preserved
  // changelist filters (#441) when they arrived from a filtered list.
  const listPath = listPathWithPreservedFilters(`/${appLabel}/${modelName}`, searchParams);
  // Heading + breadcrumb use the model's verbose labels (never the app
  // label), honouring Meta.verbose_name[_plural] (#354).
  const { singular: modelTitle, plural: modelPlural } = useModelMeta(appLabel, modelName);

  const [schema, setSchema] = useState<AddFormResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // Bumped to remount the form (clear all fields) after "Save and add
  // another" so the operator gets a fresh blank form (#154).
  const [formKey, setFormKey] = useState(0);

  useEffect(() => {
    let alive = true;
    setSchema(null);
    setLoadError(null);
    client
      .addForm(appLabel, modelName)
      .then((s) => {
        if (alive) setSchema(s);
      })
      .catch((e: unknown) => {
        if (alive) setLoadError(e instanceof Error ? e.message : 'Could not load the add form.');
      });
    return () => {
      alive = false;
    };
  }, [client, appLabel, modelName]);

  if (loadError) {
    return <EmptyState title="Couldn't open the add form" description={loadError} />;
  }
  if (!schema) return <RecordSkeleton />;

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <Breadcrumb
          items={[
            { label: 'Home', to: '/' },
            { label: modelPlural, to: listPath },
            { label: `Add ${modelTitle}` },
          ]}
          renderLink={(to, className, label) => (
            <Link to={to} className={className}>
              {label}
            </Link>
          )}
        />
        <h1 className="text-2xl font-semibold">Add {modelTitle}</h1>
      </header>
      <CreateForm
        key={formKey}
        schema={schema}
        onCreate={async (payload, action) => {
          const created = await createObject({ client, appLabel, modelName, payload });
          toast.success('Added.');
          if (action === 'addAnother') {
            setFormKey((k) => k + 1); // fresh blank form, stay on add
            return;
          }
          if (action === 'continue') {
            // Land on the new object's change view, in edit mode —
            // carrying the preserved filters forward (#441).
            navigate(
              carryPreservedFilters(`/${appLabel}/${modelName}/${created.pk}?edit=1`, searchParams),
            );
            return;
          }
          // Plain "Save" → back to the (preserved-filter) changelist.
          navigate(listPath);
        }}
        onCancel={() => navigate(listPath)}
      />
    </div>
  );
}

// Save-flow buttons available on the add view (#154). The parent routes
// navigation per action; the form only builds + submits.
type CreateSaveAction = 'save' | 'continue' | 'addAnother';

interface CreateFormProps {
  schema: AddFormResponse;
  onCreate: (payload: Record<string, WriteValue>, action: CreateSaveAction) => Promise<void>;
  onCancel: () => void;
}

function CreateForm({ schema, onCreate, onCancel }: CreateFormProps) {
  const [values, setValues] = useState<Record<string, WriteValue>>(() => {
    const init: Record<string, WriteValue> = {};
    for (const [name, field] of Object.entries(schema.fields)) {
      if (field.readonly) continue;
      if (field.type === 'manytomany') {
        // M2M starts empty on a new object; the widget produces a pk list.
        init[name] = [];
        continue;
      }
      const v = field.value;
      if (field.type === 'json') {
        // JSON editor (#242): seed the textarea with the pretty-printed
        // default (a string), or empty when there's no default.
        init[name] = v === null || v === undefined ? null : JSON.stringify(v, null, 2);
        continue;
      }
      if (field.type === 'array') {
        // ArrayField editor (#242): seed the comma-joined default (string).
        init[name] = Array.isArray(v) ? v.join(',') : null;
        continue;
      }
      if (field.type === 'range') {
        // RangeField editor (#242): unwrap the read envelope
        // `{subtype, value: {lower, upper, bounds}}` into the
        // `[lower, upper]` array `_range_endpoints` accepts (#533). A
        // missing default → two empty inputs (unbounded both sides).
        if (v && typeof v === 'object' && 'value' in v) {
          const inner = (v as { value?: unknown }).value;
          if (inner && typeof inner === 'object') {
            const lower = (inner as { lower?: unknown }).lower;
            const upper = (inner as { upper?: unknown }).upper;
            init[name] = [
              lower == null ? '' : String(lower),
              upper == null ? '' : String(upper),
            ];
            continue;
          }
        }
        init[name] = ['', ''];
        continue;
      }
      // Seed with the model default where the wire carries a scalar;
      // FK envelopes / html start empty for a new object.
      init[name] = v !== null && typeof v !== 'object' ? v : null;
    }
    return init;
  });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [nonFieldError, setNonFieldError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // prepopulated_fields (#245): slugify a target field from its sources
  // while typing (Django add-form parity). Once the operator edits a
  // target by hand we stop auto-filling it — tracked here.
  const prepopulated = schema.prepopulated_fields ?? {};
  const prepopTargets = new Set(Object.keys(prepopulated));
  const editedTargets = useRef<Set<string>>(new Set());

  function handleFieldChange(name: string, v: WriteValue): void {
    setValues((prev) => {
      const next = { ...prev, [name]: v };
      // A direct edit of a target field opts it out of further auto-fill.
      if (prepopTargets.has(name)) editedTargets.current.add(name);
      for (const [target, sources] of Object.entries(prepopulated)) {
        if (editedTargets.current.has(target)) continue;
        if (!sources.includes(name)) continue;
        const joined = sources.map((s) => (next[s] == null ? '' : String(next[s]))).join(' ');
        next[target] = slugify(joined);
      }
      return next;
    });
  }

  // Unsaved-changes guard (#290): warn on tab-close/reload once the
  // operator has typed into the new-object form.
  const initialJsonRef = useRef<string | null>(null);
  if (initialJsonRef.current === null) initialJsonRef.current = JSON.stringify(values);
  const dirty = JSON.stringify(values) !== initialJsonRef.current;
  useUnsavedGuard(dirty && !saving);

  async function runSave(action: CreateSaveAction) {
    setSaving(true);
    setErrors({});
    setNonFieldError(null);
    try {
      await onCreate(values, action);
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
        setNonFieldError(err instanceof Error ? err.message : 'Create failed.');
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await runSave('save');
  }

  const so = schema.save_options;

  // Save-flow buttons (#154) — render only what `save_options` allows;
  // default to a plain Add for older backends. Built as a function so it
  // can be rendered both at the top (when `save_on_top`, #251) and bottom.
  const renderSaveActions = () => (
    <div className="flex flex-wrap gap-2">
      {(so?.show_save ?? true) && (
        <Button type="submit" variant="primary" disabled={saving}>
          {saving ? 'Saving…' : 'Add'}
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
      {schema.fieldsets.map((fieldset, idx) => (
        <Card key={`cfs-${idx}-${fieldset.title ?? 'default'}`} title={fieldset.title ?? undefined}>
          <div className="divide-y divide-gray-100">
            {(fieldset.field_rows ?? fieldset.fields.map((f) => [f])).map((row, ri) => {
              const renderInput = (name: string) => {
                const field = schema.fields[name];
                if (!field) return null;
                return (
                  <FieldInput
                    key={name}
                    name={name}
                    field={field}
                    value={values[name] ?? null}
                    error={errors[name]}
                    onChange={(v) => handleFieldChange(name, v)}
                  />
                );
              };
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
      ))}
      {renderSaveActions()}
    </form>
  );
}
