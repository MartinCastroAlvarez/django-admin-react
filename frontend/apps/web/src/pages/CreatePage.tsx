// CreatePage — add a new object.
//
// Fetches the create-form schema from GET <app>/<model>/add/ (same
// field/fieldset shape as detail, for an unsaved object), renders the
// shared FieldInput form, and POSTs via createObject. Field-level
// validation errors come back in the envelope and render next to each
// input. On success, navigates to the new object's detail page.

import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import {
  ApiError,
  createObject,
  useApiClient,
  type AddFormResponse,
  type WriteValue,
} from '@dar/data';
import { Button, Card, EmptyState, Spinner } from '@dar/ui';

import { FieldInput } from '../components/FieldInput';
import { useToast } from '../toast';

export function CreatePage() {
  const params = useParams<{ appLabel: string; modelName: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const client = useApiClient();
  const navigate = useNavigate();
  const toast = useToast();

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
  if (!schema) return <Spinner label="Loading…" />;

  return (
    <div className="space-y-4">
      <header>
        <Link to={`/${appLabel}/${modelName}`} className="text-sm text-blue-600 hover:underline">
          ← Back to list
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">
          Add {appLabel} · {modelName}
        </h1>
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
            // Land on the new object's change view, in edit mode.
            navigate(`/${appLabel}/${modelName}/${created.pk}?edit=1`);
            return;
          }
          // Plain "Save" → back to the changelist (Django parity).
          navigate(`/${appLabel}/${modelName}`);
        }}
        onCancel={() => navigate(`/${appLabel}/${modelName}`)}
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
      const v = field.value;
      // Seed with the model default where the wire carries a scalar;
      // FK envelopes / arrays / html start empty for a new object.
      init[name] = v !== null && typeof v !== 'object' ? v : null;
    }
    return init;
  });
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [nonFieldError, setNonFieldError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function runSave(action: CreateSaveAction) {
    setSaving(true);
    setErrors({});
    setNonFieldError(null);
    try {
      await onCreate(values, action);
    } catch (err) {
      if (err instanceof ApiError && err.envelope?.error) {
        const fieldErrors = err.envelope.error.fields ?? {};
        setErrors(fieldErrors);
        if (Object.keys(fieldErrors).length === 0) {
          setNonFieldError(err.envelope.error.message || 'Create failed.');
        }
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

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {nonFieldError && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {nonFieldError}
        </div>
      )}
      {schema.fieldsets.map((fieldset, idx) => (
        <Card key={`cfs-${idx}-${fieldset.title ?? 'default'}`} title={fieldset.title ?? undefined}>
          <div className="divide-y divide-gray-100">
            {fieldset.fields.map((name) => {
              const field = schema.fields[name];
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
            })}
          </div>
        </Card>
      ))}
      {/* Save-flow buttons (#154) — render only what `save_options`
          allows; default to a plain Add for older backends. */}
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
    </form>
  );
}
