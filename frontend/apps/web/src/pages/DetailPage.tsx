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
//
// The inner pieces (read-mode sections, the edit form, the toolbar
// buttons) live in sibling modules under ./detail (#657); this file is
// just the page that wires them together.

import { useState } from 'react';
import { Clock, ExternalLink, Pencil, RefreshCw } from 'lucide-react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  createObject,
  deleteObject,
  fetchDeletePreview,
  runObjectAction,
  updateObject,
  useApiClient,
  useDetail,
  type WriteValue,
} from '@dar/data';
import { detailCollapseKey } from '@dar/customization';
import { Breadcrumb, Button, EmptyState, RefreshButton } from '@dar/ui';
import { HistoryModal } from '@dar/history';

import { RecordSkeleton } from '../components/RecordSkeleton';
import { useModelMeta } from '../useModelMeta';
import { toastMessages, useToast } from '../toast';
import { followActionRedirect } from '../action-redirect';
import { carryPreservedFilters, listPathWithPreservedFilters } from '../changelistFilters';
import { CustomViewsMenu } from './detail/CustomViewsMenu';
import { DeleteButton } from './detail/DeleteButton';
import { EditForm } from './detail/EditForm';
import { FieldsetSection } from './detail/FieldsetSection';
import { InlineSection } from './detail/InlineSection';
import { ObjectActionButton } from './detail/ObjectActionButton';

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
            {/* Render every entry in `data.object_actions` here, batch
                AND detail (#618). The API's signature classifier marks
                queryset-shaped actions as `batch` and obj_id-shaped ones
                as `detail`; the runner endpoint dispatches both correctly
                — batch is invoked as `action(modeladmin, request,
                queryset_of_one)` for the detail page's single pk, detail
                is invoked as `action(modeladmin, request, str(pk))` once.
                One `@admin.action` declaration → two surfaces: dropdown
                on the changelist, button on the detail page. A pre-1.0.6
                API omits `target` entirely; those descriptors still
                render here unfiltered. */}
            {(data.object_actions ?? [])
              .map((action) => (
              <ObjectActionButton
                key={action.name}
                action={action}
                onRun={() =>
                  runObjectAction({ client, appLabel, modelName, pk, name: action.name })
                }
                onSuccess={async ({ message, messages, redirect }) => {
                  if (redirect) {
                    // Smart-route the redirect (#620): an admin action
                    // can hand back any URL — a same-SPA path, a legacy
                    // `/admin/.../change/` page, a hijack URL, a signed
                    // S3 download. React Router's `navigate` only
                    // routes WITHIN the SPA mount, so non-SPA URLs
                    // silently no-op'd before. `followActionRedirect`
                    // picks `navigate` vs `window.location.assign`
                    // based on origin + mount.
                    const mountMeta = document
                      .querySelector<HTMLMetaElement>('meta[name="dar-mount"]')
                      ?.content?.trim();
                    const mount = (mountMeta ?? '/').replace(/\/?$/, '/');
                    followActionRedirect({ redirect, mount, navigate });
                    return;
                  }
                  await refresh();
                  // Dispatch by Django level tag (#632) — error /
                  // warning levels must NOT toast green. Falls back to a
                  // single-line success toast for v1.4.x APIs that don't
                  // emit `messages[]`.
                  if (messages && messages.length > 0) {
                    toastMessages(toast, messages);
                  } else {
                    toast.success(message || 'Done');
                  }
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
