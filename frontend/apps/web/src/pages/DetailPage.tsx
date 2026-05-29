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
import {
  ChevronDown,
  Clock,
  ExternalLink,
  Pencil,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  ApiError,
  createObject,
  deleteObject,
  fetchDeletePreview,
  runObjectAction,
  updateObject,
  useApiClient,
  useDetail,
  type CustomView,
  type DeletePreviewResponse,
  type DetailResponse,
  type FieldDescriptor,
  type FieldsetDescriptor,
  type InlineDescriptor,
  type InlineWriteItem,
  type InlineWritePayload,
  type ObjectActionDescriptor,
  type WriteValue,
} from '@dar/data';
import { detailCollapseKey, usePersistedState } from '@dar/customization';
import { Breadcrumb, Button, Card, EmptyState, Modal, RefreshButton, Table } from '@dar/ui';
import { FieldValueView } from '@dar/details';
import { FieldInput, InlineEditor } from '@dar/form';
import { HistoryModal } from '@dar/history';

import { RecordSkeleton } from '../components/RecordSkeleton';
import { useModelMeta } from '../useModelMeta';
import { useToast } from '../toast';
import { carryPreservedFilters, listPathWithPreservedFilters } from '../changelistFilters';
import { useUnsavedGuard } from '../useUnsavedGuard';

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
        className="text-primary hover:underline"
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
  return <FieldValueView value={field.value} type={field.type} />;
}

// Render one fieldset in the read view. Every section is collapsible
// behind a caret (#359) and remembers its open/closed state per model +
// section in localStorage. The default honours Django's fieldset
// `classes` (#306): a `collapse` section starts collapsed, the rest
// start open; any `description` shows as section help text under the
// title. A saved preference (if present) wins over that default.
function FieldsetSection({
  fieldset,
  fields,
  persistKey,
}: {
  fieldset: FieldsetDescriptor;
  fields: Record<string, FieldDescriptor>;
  persistKey: string;
}) {
  // Default open unless Django's `collapse` class says otherwise; a saved
  // preference wins. Persistence is centralized in @dar/customization.
  const startsCollapsed = (fieldset.classes ?? []).includes('collapse');
  const [open, setOpen] = usePersistedState<boolean>(persistKey, !startsCollapsed);
  const toggle = (): void => setOpen((o) => !o);

  return (
    <Card>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-left text-base font-semibold text-gray-900"
      >
        <span>{fieldset.title ?? 'Details'}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open ? (
        <div className="mt-3">
          {fieldset.description ? (
            <p className="mb-3 text-xs text-gray-500">{fieldset.description}</p>
          ) : null}
          <dl className="divide-y divide-gray-100">
            {(fieldset.field_rows ?? fieldset.fields.map((f) => [f])).map((row, ri) => {
              // A single-field row keeps the wide label | value layout; a
              // multi-field row (Django tuple grouping, #382) lays its
              // fields side by side, each label-above-value.
              if (row.length === 1) {
                const field = fields[row[0] as string];
                if (!field) return null;
                return (
                  <div key={ri} className="grid grid-cols-3 gap-4 py-2 text-sm">
                    <dt className="text-gray-500">{field.label}</dt>
                    <dd className="col-span-2 min-w-0 whitespace-pre-wrap break-words text-gray-900">
                      <DetailValue field={field} />
                    </dd>
                  </div>
                );
              }
              return (
                <div
                  key={ri}
                  className="grid gap-4 py-2 text-sm"
                  style={{ gridTemplateColumns: `repeat(${row.length}, minmax(0, 1fr))` }}
                >
                  {row.map((name) => {
                    const field = fields[name];
                    if (!field) return null;
                    return (
                      <div key={name}>
                        <dt className="text-gray-500">{field.label}</dt>
                        <dd className="mt-0.5 min-w-0 whitespace-pre-wrap break-words text-gray-900">
                          <DetailValue field={field} />
                        </dd>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </dl>
        </div>
      ) : null}
    </Card>
  );
}

export interface DetailPageProps {
  /** Open the page directly in edit mode (Django-admin URL alias
   *  `/<app>/<model>/<pk>/change/`, #601). Also still triggered by
   *  the existing `?edit=1` query param from "Save and continue
   *  editing" (#154). */
  initialEditing?: boolean;
  /** Open the History modal on first paint (Django-admin URL alias
   *  `/<app>/<model>/<pk>/history/`, #601). The user can still close
   *  it; this just sets the initial state. */
  initialHistoryOpen?: boolean;
}

export function DetailPage({
  initialEditing = false,
  initialHistoryOpen = false,
}: DetailPageProps = {}) {
  const params = useParams<{ appLabel: string; modelName: string; pk: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const pk = params.pk ?? '';
  const client = useApiClient();
  const navigate = useNavigate();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const { data, loading, error, refresh } = useDetail({ client, appLabel, modelName, pk });

  // Open straight in edit mode when arriving via "Save and continue
  // editing" from the add form (`?edit=1`); otherwise start read-only.
  // Initial mode is the OR of (a) the Django-admin URL alias the router
  // matched and (b) the existing `?edit=1` "Save and continue editing"
  // round-trip — either drops the user in edit mode on first paint
  // (#154, #601).
  const [editing, setEditing] = useState(
    () => initialEditing || searchParams.get('edit') === '1',
  );
  const [historyOpen, setHistoryOpen] = useState(initialHistoryOpen);
  const { plural: modelPlural } = useModelMeta(appLabel, modelName);

  // Detail-page action buttons (#571): per-object actions only, via
  // `django-object-actions` (`change_actions`). Surfaced by the API as
  // `data.object_actions` and rendered below via <ObjectActionButton>.
  // The original #555 attempt — running `ModelAdmin.actions` (changelist
  // bulk actions) on a one-pk slice — was the wrong primitive: bulk
  // actions are *list* semantics and confused the operator on a
  // single-object page. Reverted in v1.0.2.

  if (loading && !data) return <RecordSkeleton />;
  if (error && !data) {
    return <EmptyState title="Couldn't load the object" description={error.message} />;
  }
  if (!data) return null;

  const canChange = data.permissions.change;
  const canDelete = data.permissions.delete;

  // Where "back to the list" goes — restoring the operator's preserved
  // changelist filters (#441) when they arrived from a filtered list.
  const listPath = listPathWithPreservedFilters(`/${appLabel}/${modelName}`, searchParams);

  return (
    <div className="space-y-4">
      {/* Header (#572): the title is the page's most important element
          and gets as much horizontal space as it needs (`flex-1
          min-w-0`); the toolbar is `shrink-0` and only pushes the title
          when it genuinely can't fit on its row. `justify-end` on the
          toolbar's flex-wrap keeps wrapped button rows flush right to
          the page padding, instead of left-aligned within their column. */}
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <Breadcrumb
            items={[
              { label: 'Home', to: '/' },
              { label: modelPlural, to: listPath },
              { label: data.label },
            ]}
            renderLink={(to, className, label) => (
              <Link to={to} className={className}>
                {label}
              </Link>
            )}
          />
          <h1 className="text-2xl font-semibold">{data.label}</h1>
        </div>
        {!editing && (
          <div className="flex shrink-0 flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={() => setHistoryOpen(true)}
              aria-label="History"
              title="History"
              // Icon-only (#608) — the clock icon already speaks for
              // itself alongside the other small icon-only buttons
              // (Refresh, the per-object actions); the "History"
              // label was redundant chrome on a crowded header.
              className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-2 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <Clock className="h-4 w-4" aria-hidden />
            </button>
            {data.view_on_site_url && (
              <a
                href={data.view_on_site_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <ExternalLink className="h-4 w-4" aria-hidden /> View on site
              </a>
            )}
            {data.custom_views && data.custom_views.length > 0 && (
              <CustomViewsMenu views={data.custom_views} />
            )}
            {/* Object-level change-page actions (#236) — django-object-actions
                `change_actions` parity. The backend re-validates the action
                name against its permitted set, so a button can never run an
                action the user isn't allowed to. On success we re-fetch the
                detail payload (computed/readonly fields may have changed) and
                navigate if the action returned a redirect. No full reload. */}
            {(data.object_actions ?? []).map((action) => (
              <ObjectActionButton
                key={action.name}
                action={action}
                onRun={() =>
                  runObjectAction({ client, appLabel, modelName, pk, name: action.name })
                }
                onSuccess={async (message, redirect) => {
                  if (redirect) {
                    navigate(redirect);
                    return;
                  }
                  await refresh();
                  toast.success(message || 'Done');
                }}
                onError={(message) => toast.error(message)}
              />
            ))}
            {/* Refresh (#592): refetch the object + inlines + history
                with no full page reload. Placed between the actions
                cluster and the Edit / Delete pair so destructive
                buttons stay at the trailing edge. */}
            <RefreshButton
              onRefresh={refresh}
              tooltip="Refresh"
              icon={<RefreshCw className="h-4 w-4" aria-hidden />}
            />
            {canChange && (
              <Button variant="primary" onClick={() => setEditing(true)}>
                <span className="inline-flex items-center gap-1.5">
                  <Pencil className="h-4 w-4" aria-hidden /> Edit
                </span>
              </Button>
            )}
            {canDelete && (
              <DeleteButton
                label={data.label}
                loadPreview={() => fetchDeletePreview({ client, appLabel, modelName, pk })}
                onConfirm={async () => {
                  await deleteObject({ client, appLabel, modelName, pk });
                  toast.success(`Deleted “${data.label}”.`);
                  navigate(listPath);
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
              toast.success('Created a new object.');
              navigate(
                data.save_options?.save_as_continue
                  ? carryPreservedFilters(
                      `/${appLabel}/${modelName}/${created.pk}?edit=1`,
                      searchParams,
                    )
                  : listPath,
              );
              return;
            }
            await updateObject({ client, appLabel, modelName, pk, payload });
            toast.success('Saved.');
            if (action === 'continue') {
              await refresh(); // stay in edit mode with the saved values
              return;
            }
            if (action === 'addAnother') {
              navigate(carryPreservedFilters(`/${appLabel}/${modelName}/add`, searchParams));
              return;
            }
            // Plain "Save" → back to the (preserved-filter) changelist.
            navigate(listPath);
          }}
        />
      ) : (
        <>
          {data.fieldsets.map((fieldset, idx) => (
            <FieldsetSection
              key={`fs-${idx}-${fieldset.title ?? 'default'}`}
              fieldset={fieldset}
              fields={data.fields}
              persistKey={detailCollapseKey(appLabel, modelName, idx, fieldset.title ?? 'default')}
            />
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

      {historyOpen && (
        <HistoryModal
          appLabel={appLabel}
          modelName={modelName}
          pk={pk}
          onClose={() => setHistoryOpen(false)}
        />
      )}
    </div>
  );
}

// One object-level change-page action button (#236). Disables + shows a
// spinner while the POST is in flight; on success the parent re-fetches
// the detail payload (so computed/readonly fields reflect the action) and
// toasts, or navigates when the action returned a redirect. No full reload.
function ObjectActionButton({
  action,
  onRun,
  onSuccess,
  onError,
}: {
  action: ObjectActionDescriptor;
  onRun: () => Promise<{ ok: boolean; message?: string; redirect?: string }>;
  onSuccess: (message: string | undefined, redirect: string | undefined) => Promise<void> | void;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="secondary"
      loading={busy}
      disabled={busy}
      title={action.description}
      onClick={async () => {
        setBusy(true);
        try {
          const result = await onRun();
          if (result.ok) {
            await onSuccess(result.message, result.redirect);
          } else {
            onError(result.message || 'The action could not be completed.');
          }
        } catch (err) {
          // A raising action callable comes back as a 400 (never a 500);
          // the client throws an ApiError. The 400 body is `{ok, error}`,
          // and the backend keeps that message generic on purpose, so we
          // surface a friendly fallback rather than the raw "HTTP 400".
          if (err instanceof ApiError) {
            const raw = err.envelope as unknown as { error?: unknown } | null;
            const detail =
              typeof raw?.error === 'string' ? raw.error : err.envelope?.error?.message;
            onError(detail || 'The action could not be completed.');
          } else {
            onError(err instanceof Error ? err.message : 'The action could not be completed.');
          }
        } finally {
          setBusy(false);
        }
      }}
    >
      {action.label}
    </Button>
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

// Custom admin views (#439): bespoke admin pages the consumer wired via
// ModelAdmin.get_urls(). The SPA can't render the Django template, so it
// links out — a real anchor that opens the legacy-admin-rendered page in
// a new tab. A single view renders as one button; several collapse into
// an unobtrusive "More" dropdown so the toolbar stays tidy. Closes on
// outside-click / Escape.
function CustomViewsMenu({ views }: { views: CustomView[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (e: MouseEvent): void => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const linkClass =
    'flex items-center gap-1.5 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 whitespace-nowrap';

  // Single view → render it inline as one button (no need for a menu).
  if (views.length === 1) {
    const v = views[0] as CustomView;
    return (
      <a
        href={v.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <ExternalLink className="h-4 w-4" aria-hidden /> {v.label}
      </a>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        More
        <ChevronDown
          className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-10 mt-1 min-w-[12rem] overflow-hidden rounded-md border border-gray-200 bg-white py-1 shadow-lg"
        >
          {views.map((v) => (
            <a
              key={v.name}
              href={v.url}
              target="_blank"
              rel="noopener noreferrer"
              role="menuitem"
              className={linkClass}
              onClick={() => setOpen(false)}
            >
              <ExternalLink className="h-4 w-4 shrink-0" aria-hidden /> {v.label}
            </a>
          ))}
        </div>
      )}
    </div>
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
        <span className="inline-flex items-center gap-1.5">
          <Trash2 className="h-4 w-4" aria-hidden /> Delete
        </span>
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

// CollapsedEmptyInline (#591) — a slim card showing only the inline's
// title + a caret toggle. The body (the "No X yet" copy + a hint to
// enter edit mode) is hidden by default; clicking the title expands
// it. Default-collapsed every page load — per-user persistence isn't
// worth the storage for a detail-page hint.
function CollapsedEmptyInline({ label }: { label: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-left text-base font-semibold text-gray-900"
      >
        <span>{label}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open ? (
        <p className="mt-3 text-sm text-gray-500">
          No {label.toLowerCase()} yet. Click <span className="font-medium">Edit</span> to
          add the first one.
        </p>
      ) : null}
    </Card>
  );
}

function InlineSection({ inline }: { inline: InlineDescriptor }) {
  // Empty inline (#591):
  // - Not addable → hide the whole section (Option A). Empty + read-only
  //   has zero information value and just lengthens the page.
  // - Addable → render as a single-line collapsed card with a caret
  //   (Option B). The operator can see the inline EXISTS (so they
  //   know to click Edit to add a first child) but the "No X yet"
  //   placeholder no longer eats vertical space on every load.
  if (inline.rows.length === 0) {
    if (!inline.can_add) return null;
    return <CollapsedEmptyInline label={inline.label} />;
  }

  // Per-row link to the child's own change page (#384 — Django's
  // InlineModelAdmin.show_change_link). The backend only sets the flag
  // when the child is registered, so the target always resolves.
  const changeLinkTo = (pk: string | number): string =>
    `/${inline.child.app_label}/${inline.child.model_name}/${pk}`;

  if (inline.kind === 'tabular') {
    const columns = [
      ...inline.fields.map((f) => ({
        key: f.name,
        header: f.label,
        // The pk column never truncates (#418) — a UUID/explicit pk is the
        // row's identity and link target and must stay fully readable.
        noTruncate: f.name === inline.pk_field,
        render: (row: (typeof inline.rows)[number]) => (
          <FieldValueView value={row.fields[f.name]} type={f.type} />
        ),
      })),
      ...(inline.show_change_link
        ? [
            {
              key: '__change_link',
              header: '',
              render: (row: (typeof inline.rows)[number]) => (
                <Link to={changeLinkTo(row.pk)} className="text-primary hover:underline">
                  Edit
                </Link>
              ),
            },
          ]
        : []),
    ];
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
          <div key={row.pk} className="py-3">
            <dl className="grid grid-cols-3 gap-4 text-sm">
              {inline.fields.map((f) => (
                <div key={f.name} className="contents">
                  <dt className="text-gray-500">{f.label}</dt>
                  <dd className="col-span-2 min-w-0 whitespace-pre-wrap break-words text-gray-900">
                    <FieldValueView value={row.fields[f.name]} type={f.type} />
                  </dd>
                </div>
              ))}
            </dl>
            {inline.show_change_link && (
              <div className="mt-2">
                <Link to={changeLinkTo(row.pk)} className="text-sm text-primary hover:underline">
                  Edit
                </Link>
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
