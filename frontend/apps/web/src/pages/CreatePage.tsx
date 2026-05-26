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

export function CreatePage() {
  const params = useParams<{ appLabel: string; modelName: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const client = useApiClient();
  const navigate = useNavigate();

  const [schema, setSchema] = useState<AddFormResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

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
        schema={schema}
        onCreate={async (payload) => {
          const created = await createObject({ client, appLabel, modelName, payload });
          navigate(`/${appLabel}/${modelName}/${created.pk}`);
        }}
        onCancel={() => navigate(`/${appLabel}/${modelName}`)}
      />
    </div>
  );
}

interface CreateFormProps {
  schema: AddFormResponse;
  onCreate: (payload: Record<string, WriteValue>) => Promise<void>;
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    setNonFieldError(null);
    try {
      await onCreate(values);
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
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={saving}>
          {saving ? 'Saving…' : 'Add'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
