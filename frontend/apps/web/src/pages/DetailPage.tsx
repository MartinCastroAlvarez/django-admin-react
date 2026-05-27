// DetailPage — view + edit + delete one object.
//
// Read view renders the admin's fieldsets as a definition list plus
// any inlines (#54). Edit mode swaps each field row for a FieldInput
// (honouring readonly + type); Save PATCHes via updateObject and
// surfaces field-level errors from the validation envelope. Delete
// opens a confirm dialog — the shared @dar/ui Modal (translucent dark
// overlay, Esc / backdrop close), the same primitive the list's filter
// and bulk-action confirms use — then DELETEs and returns to the list.
// Edit/Delete are gated by the `permissions` block the API returns.

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  ApiError,
  createObject,
  deleteObject,
  fetchDeletePreview,
  updateObject,
  useApiClient,
  useDetail,
  type DeletePreviewResponse,
  type DetailResponse,
  type FieldDescriptor,
  type InlineDescriptor,
  type InlineWriteItem,
  type InlineWritePayload,
  type WriteValue,
} from '@dar/data';
import { Button, Card, EmptyState, Modal, Spinner, Table } from '@dar/ui';

import { FieldInput } from '../components/FieldInput';
import { FieldValueView } from '../components/FieldValueView';
import { InlineEditor } from '../components/InlineEditor';

// Render a detail field's value. ForeignKey values become a navigable
// link to the related object's detail page (#184 — Django-admin
// parity), using the descriptor's `to` (the FK target's real
// app_label + model_name) so the URL round-trips through resolve_model.
// Everything else defers to FieldValueView.
function DetailValue({ field }: { field: FieldDescriptor }) {
  const v = field.value;
  if (
    field.type === 'foreignkey' &&
    field.to &&
    v &&
    typeof v === 'object' &&
    !Array.isArray(v) &&
    'id' in v
  ) {
    const fk = v as { id: number | string; label: string };
    return (
      <Link
        to={`/${field.to.app_label}/${field.to.model_name}/${fk.id}`}
        className="text-blue-600 hover:underline"
      >
        {fk.label}
      </Link>
    );
  }
  // Choice field: show the human label for the stored value (Django's
  // get_FOO_display parity). The editor still submits the raw value via
  // `field.value`; this only changes the read-mode rendering. Scalar
  // values only — FK / file / html envelopes are objects handled above
  // or by FieldValueView.
  if (field.choices && field.choices.length > 0 && v !== null && typeof v !== 'object') {
    const match = field.choices.find((o) => String(o.value) === String(v));
    if (match) return <>{match.label}</>;
  }
  return <FieldValueView value={field.value} />;
}

export function DetailPage() {
  const params = useParams<{ appLabel: string; modelName: string; pk: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const pk = params.pk ?? '';
  const client = useApiClient();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { data, loading, error, refresh } = useDetail({ client, appLabel, modelName, pk });

  // Open straight in edit mode when arriving via "Save and continue
  // editing" from the add form (`?edit=1`); otherwise start read-only.
  const [editing, setEditing] = useState(() => searchParams.get('edit') === '1');

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
                loadPreview={() => fetchDeletePreview({ client, appLabel, modelName, pk })}
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
          onSave={async (payload, action) => {
            // "Save as new" creates a fresh object from the current
            // values (Django's save_as), then lands on the new object's
            // change view or the changelist per save_as_continue.
            if (action === 'saveAsNew') {
              // Create from the field values only — inlines don't carry
              // over to a brand-new object on "Save as new".
              const createPayload: Record<string, WriteValue> = {};
              for (const [key, value] of Object.entries(payload)) {
                if (key !== 'inlines') createPayload[key] = value as WriteValue;
              }
              const created = await createObject({
                client,
                appLabel,
                modelName,
                payload: createPayload,
              });
              navigate(
                data.save_options?.save_as_continue
                  ? `/${appLabel}/${modelName}/${created.pk}?edit=1`
                  : `/${appLabel}/${modelName}`,
              );
              return;
            }
            await updateObject({ client, appLabel, modelName, pk, payload });
            if (action === 'continue') {
              await refresh(); // stay in edit mode with the saved values
              return;
            }
            if (action === 'addAnother') {
              navigate(`/${appLabel}/${modelName}/add`);
              return;
            }
            // Plain "Save" → back to the changelist (Django parity).
            navigate(`/${appLabel}/${modelName}`);
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
                        <DetailValue field={field} />
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

// Which save-flow button was pressed (Django parity, #154). The parent
// routes navigation per action; the form only builds + submits.
type SaveAction = 'save' | 'continue' | 'addAnother' | 'saveAsNew';

interface EditFormProps {
  data: DetailResponse;
  onCancel: () => void;
  onSave: (payload: import('@dar/data').UpdatePayload, action: SaveAction) => Promise<void>;
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
  // Inline write items collected from each InlineEditor, keyed by name.
  const [inlineItems, setInlineItems] = useState<Record<string, InlineWriteItem[]>>({});

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await runSave('save');
  }

  const so = data.save_options;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {nonFieldError && (
        <div className="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {nonFieldError}
        </div>
      )}
      {data.fieldsets.map((fieldset, idx) => (
        <Card key={`efs-${idx}-${fieldset.title ?? 'default'}`} title={fieldset.title ?? undefined}>
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

      {/* Save-flow buttons (#154) — render only what `save_options`
          allows; default to a plain Save for older backends. */}
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
    </form>
  );
}

interface DeleteButtonProps {
  label: string;
  loadPreview: () => Promise<DeletePreviewResponse>;
  onConfirm: () => Promise<void>;
}

// Delete affordance: a danger button that opens a confirm dialog (the
// shared @dar/ui Modal). On open it fetches the cascade preview (#153 /
// Django admin's delete-confirmation parity) so the operator sees what
// else gets removed, what's PROTECT-blocked, and which extra delete
// perms are missing BEFORE the single destructive click. The Delete
// button is disabled while the preview says `can_delete: false`
// (protected rows or missing perms). The preview fetch is best-effort:
// if it fails, the dialog degrades to the plain confirm rather than
// blocking a legitimate delete. While the DELETE is in flight the modal
// can't be dismissed so it can't be double-fired.
function DeleteButton({ label, loadPreview, onConfirm }: DeleteButtonProps) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<DeletePreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Latest-ref so the fetch fires only when the modal *opens*, not on
  // every parent re-render (e.g. the background list/detail refetch).
  const loadRef = useRef(loadPreview);
  loadRef.current = loadPreview;

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    setPreviewLoading(true);
    loadRef
      .current()
      .then((p) => {
        if (!cancelled) setPreview(p);
      })
      .catch(() => {
        // Best-effort: a failed preview must not block a valid delete.
        if (!cancelled) setPreview(null);
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const close = () => {
    if (busy) return;
    setOpen(false);
    setErr(null);
    setPreview(null);
  };

  // Block the destructive action only when the preview positively says
  // so — never when it's still loading or failed to load.
  const blocked = preview !== null && !preview.can_delete;

  return (
    <>
      <Button variant="danger" onClick={() => setOpen(true)}>
        Delete
      </Button>
      {open && (
        <Modal
          title="Delete object"
          onClose={close}
          footer={
            <>
              <Button variant="secondary" disabled={busy} onClick={close}>
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={busy || previewLoading || blocked}
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
                {busy ? 'Deleting…' : 'Delete'}
              </Button>
            </>
          }
        >
          <p className="text-sm text-gray-700">
            Are you sure you want to delete <span className="font-medium">“{label}”</span>? This
            action cannot be undone.
          </p>

          {previewLoading && (
            <p className="mt-3 text-sm text-gray-500">Checking what this affects…</p>
          )}

          {preview && preview.cascade.length > 0 && (
            <div className="mt-3 text-sm text-gray-700">
              <p className="font-medium">This will also delete:</p>
              <ul className="mt-1 list-disc pl-5">
                {preview.cascade.map((c) => (
                  <li key={c.model}>
                    {c.count} {c.model}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {preview && preview.protected.length > 0 && (
            <div className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              <p className="font-medium">Blocked — protected related objects:</p>
              <ul className="mt-1 list-disc pl-5">
                {preview.protected.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {preview && preview.perms_needed.length > 0 && (
            <div className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              You don’t have permission to delete: {preview.perms_needed.join(', ')}.
            </div>
          )}

          {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
        </Modal>
      )}
    </>
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
