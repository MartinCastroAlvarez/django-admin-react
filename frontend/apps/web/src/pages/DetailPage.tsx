// DetailPage — view + edit + delete one object.
//
// Read view renders the admin's fieldsets as a definition list plus
// any inlines (#54). Edit mode swaps each field row for a FieldInput
// (honouring readonly + type); Save PATCHes via updateObject and
// surfaces field-level errors from the validation envelope. Delete
// confirms inline, then DELETEs and returns to the list. Edit/Delete
// are gated by the `permissions` block the API returns.

import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import {
  ApiError,
  deleteObject,
  updateObject,
  useApiClient,
  useDetail,
  type DetailResponse,
  type InlineDescriptor,
  type WriteValue,
} from '@dar/data';
import { Button, Card, EmptyState, Spinner, Table } from '@dar/ui';

import { FieldInput } from '../components/FieldInput';
import { FieldValueView } from '../components/FieldValueView';

export function DetailPage() {
  const params = useParams<{ appLabel: string; modelName: string; pk: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const pk = params.pk ?? '';
  const client = useApiClient();
  const navigate = useNavigate();
  const { data, loading, error, refresh } = useDetail({ client, appLabel, modelName, pk });

  const [editing, setEditing] = useState(false);

  if (loading && !data) return <Spinner label="Loading…" />;
  if (error && !data) {
    return <EmptyState title="Couldn't load the object" description={error.message} />;
  }
  if (!data) return null;

  const canChange = data.permissions.change;
  const canDelete = data.permissions.delete;

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <Link to={`/${appLabel}/${modelName}`} className="text-sm text-blue-600 hover:underline">
            ← Back to list
          </Link>
          <h1 className="mt-1 text-2xl font-semibold">{data.label}</h1>
          <p className="text-sm text-gray-500">
            {appLabel} · {modelName} · #{data.pk}
          </p>
        </div>
        {!editing && (
          <div className="flex gap-2">
            {canChange && (
              <Button variant="primary" onClick={() => setEditing(true)}>
                Edit
              </Button>
            )}
            {canDelete && (
              <DeleteButton
                label={data.label}
                onConfirm={async () => {
                  await deleteObject({ client, appLabel, modelName, pk });
                  navigate(`/${appLabel}/${modelName}`);
                }}
              />
            )}
          </div>
        )}
      </header>

      {editing ? (
        <EditForm
          data={data}
          onCancel={() => setEditing(false)}
          onSave={async (payload) => {
            await updateObject({ client, appLabel, modelName, pk, payload });
            await refresh();
            setEditing(false);
          }}
        />
      ) : (
        <>
          {data.fieldsets.map((fieldset, idx) => (
            <Card
              key={`fs-${idx}-${fieldset.title ?? 'default'}`}
              title={fieldset.title ?? undefined}
            >
              <dl className="divide-y divide-gray-100">
                {fieldset.fields.map((name) => {
                  const field = data.fields[name];
                  if (!field) return null;
                  return (
                    <div key={name} className="grid grid-cols-3 gap-4 py-2 text-sm">
                      <dt className="text-gray-500">{field.label}</dt>
                      <dd className="col-span-2 whitespace-pre-wrap text-gray-900">
                        <FieldValueView value={field.value} />
                      </dd>
                    </div>
                  );
                })}
              </dl>
            </Card>
          ))}

          {/* Inlines (#54): the backend surfaces ModelAdmin.inlines + their
              existing rows on the detail response. Tabular → a table,
              Stacked → a card stack. Read rendering; edit affordances are
              a follow-up gated by the per-inline can_* flags. */}
          {(data.inlines ?? [])
            .filter((inline) => inline.can_view)
            .map((inline) => (
              <InlineSection key={inline.name} inline={inline} />
            ))}
        </>
      )}
    </div>
  );
}

interface EditFormProps {
  data: DetailResponse;
  onCancel: () => void;
  onSave: (payload: Record<string, WriteValue>) => Promise<void>;
}

function initialValueFor(field: DetailResponse['fields'][string]): WriteValue {
  const v = field.value;
  if (v === null || v === undefined) return null;
  if (typeof v === 'object') {
    // FK envelope {id,label} → id; arrays / html → leave null (not edited here).
    if (!Array.isArray(v) && 'id' in v) return v.id;
    return null;
  }
  return v;
}

function EditForm({ data, onCancel, onSave }: EditFormProps) {
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    setNonFieldError(null);
    try {
      await onSave(values);
    } catch (err) {
      if (err instanceof ApiError && err.envelope?.error) {
        const fieldErrors = err.envelope.error.fields ?? {};
        setErrors(fieldErrors);
        if (Object.keys(fieldErrors).length === 0) {
          setNonFieldError(err.envelope.error.message || 'Save failed.');
        }
      } else {
        setNonFieldError(err instanceof Error ? err.message : 'Save failed.');
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
      {data.fieldsets.map((fieldset, idx) => (
        <Card
          key={`efs-${idx}-${fieldset.title ?? 'default'}`}
          title={fieldset.title ?? undefined}
        >
          <div className="divide-y divide-gray-100">
            {fieldset.fields.map((name) => {
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
            })}
          </div>
        </Card>
      ))}
      <div className="flex gap-2">
        <Button type="submit" variant="primary" disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

interface DeleteButtonProps {
  label: string;
  onConfirm: () => Promise<void>;
}

function DeleteButton({ label, onConfirm }: DeleteButtonProps) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (!confirming) {
    return (
      <Button variant="danger" onClick={() => setConfirming(true)}>
        Delete
      </Button>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600">Delete “{label}”?</span>
      <Button
        variant="danger"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setErr(null);
          try {
            await onConfirm();
          } catch (e) {
            setErr(e instanceof Error ? e.message : 'Delete failed.');
            setBusy(false);
          }
        }}
      >
        {busy ? 'Deleting…' : 'Confirm'}
      </Button>
      <Button variant="secondary" disabled={busy} onClick={() => setConfirming(false)}>
        Cancel
      </Button>
      {err && <span className="text-xs text-red-600">{err}</span>}
    </div>
  );
}

function InlineSection({ inline }: { inline: InlineDescriptor }) {
  if (inline.rows.length === 0) {
    return (
      <Card title={inline.label}>
        <p className="py-4 text-sm text-gray-500">No {inline.label.toLowerCase()} yet.</p>
      </Card>
    );
  }

  if (inline.kind === 'tabular') {
    const columns = inline.fields.map((f) => ({
      key: f.name,
      header: f.label,
      render: (row: (typeof inline.rows)[number]) => <FieldValueView value={row.fields[f.name]} />,
    }));
    return (
      <Card title={inline.label}>
        <Table columns={columns} rows={inline.rows} rowKey={(r) => r.pk} />
      </Card>
    );
  }

  // Stacked: one definition list per child row.
  return (
    <Card title={inline.label}>
      <div className="divide-y divide-gray-200">
        {inline.rows.map((row) => (
          <dl key={row.pk} className="grid grid-cols-3 gap-4 py-3 text-sm">
            {inline.fields.map((f) => (
              <div key={f.name} className="contents">
                <dt className="text-gray-500">{f.label}</dt>
                <dd className="col-span-2 whitespace-pre-wrap text-gray-900">
                  <FieldValueView value={row.fields[f.name]} />
                </dd>
              </div>
            ))}
          </dl>
        ))}
      </div>
    </Card>
  );
}
