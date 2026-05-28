// ListPage — paginated table view for one model.
//
// Reads from `useList` (in @dar/data), which talks to the list
// endpoint via @dar/api. Sorting, search, and pagination are
// controlled state local to this page; cache/network management is
// the data layer's job.

import { useEffect, useMemo, useRef, useState } from 'react';
import { GripVertical, Settings2, X } from 'lucide-react';
import { Link, useHref, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { useApiClient, useList, type ActionDescriptor, type ListRow } from '@dar/data';
import {
  columnsKey,
  columnWidthsKey,
  filtersKey,
  readJSON,
  removeKey,
  usePersistedSet,
  usePersistedState,
  writeJSON,
} from '@dar/customization';
import {
  Breadcrumb,
  Button,
  Card,
  Checkbox,
  EmptyState,
  Modal,
  Pagination,
  RecordCardList,
  Table,
  useMediaQuery,
} from '@dar/ui';
import { FieldValueView } from '@dar/details';
import { ListSkeleton } from '@dar/list';
import { FilterBar } from '@dar/search';

import { useToast } from '../toast';
import { CHANGELIST_FILTERS_PARAM, withPreservedFilters } from '../changelistFilters';

// Query params the page manages itself; everything else is a
// `list_filter` key. `all` is Django's "Show all" flag (#385), not a
// filter, so it never becomes a chip or a persisted saved-view entry.
const RESERVED_PARAMS = new Set(['q', 'page', 'all', CHANGELIST_FILTERS_PARAM]);

// `date_hierarchy` drill-down params (Django's standard year/month/day).
// They DO flow to the backend (as non-reserved params), but they're not
// `list_filter` keys: excluded from the persisted "saved view" so a date
// drill doesn't silently resurrect on a later bare visit.
const DATE_PARAMS = new Set(['year', 'month', 'day']);

export function ListPage() {
  const params = useParams<{ appLabel: string; modelName: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const navigate = useNavigate();
  // Router basename (the SPA mount) so row anchors carry a full, openable
  // href for native open-in-new-tab (#253).
  const hrefBase = useHref('/').replace(/\/$/, '');
  // Below Tailwind's `md` breakpoint (768px) a wide table is unreadable on
  // phones/tablets — render the same rows as stacked record-cards instead
  // (#421). Switching in JS (not a CSS `hidden`/`md:block` pair) keeps a
  // single layout in the DOM, so there are no duplicate inputs/checkboxes.
  const isNarrow = useMediaQuery('(max-width: 767px)');
  const client = useApiClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // Search, page, and filters all live in the URL so a reload restores
  // the exact view (ACCEPTANCE N-3). Filters are every non-reserved
  // query param, keyed by the descriptor `name`.
  const q = searchParams.get('q') ?? '';
  const page = Number(searchParams.get('page') ?? '1') || 1;
  // "Show all" (#385): the URL is the source of truth — `?all` present
  // means show-all is active. Like Django's ALL_VAR, only presence matters.
  const showAll = searchParams.has('all');

  const activeFilters = useMemo(() => {
    const out: Record<string, string> = {};
    for (const [key, value] of searchParams.entries()) {
      if (!RESERVED_PARAMS.has(key) && value !== '') out[key] = value;
    }
    return out;
  }, [searchParams]);

  const { data, loading, error, refresh } = useList({
    client,
    appLabel,
    modelName,
    q,
    page,
    all: showAll,
    filters: activeFilters,
  });

  const [searchDraft, setSearchDraft] = useState(q);
  // Row selection (page-scoped, matches Django's changelist) drives
  // the Actions dropdown's visibility (#182).
  const [selected, setSelected] = useState<Set<string | number>>(new Set());
  const [actionsOpen, setActionsOpen] = useState(false);
  const [runningAction, setRunningAction] = useState(false);
  // The action awaiting confirmation (#206) — drives the styled
  // confirm modal instead of the native window.confirm.
  const [pendingAction, setPendingAction] = useState<ActionDescriptor | null>(null);
  // Inline list_editable edits (#243): pending cell changes keyed by
  // pk → field → string value, submitted together via the bulk PATCH.
  const [edits, setEdits] = useState<Record<string, Record<string, string>>>({});
  const [savingEdits, setSavingEdits] = useState(false);
  // Column customizer (#196): hidden columns persist per app/model so the
  // operator's layout survives reloads. A UI preference (not data) —
  // stored via @dar/customization, the single home for such prefs.
  const [hiddenCols, setHiddenCols] = usePersistedSet(columnsKey(appLabel, modelName));
  const [colsOpen, setColsOpen] = useState(false);

  // Drag-to-resize column widths, persisted per app/model (a UI
  // preference, like hidden columns) via @dar/customization. The Table
  // owns the drag interaction; we just hold + persist the px widths.
  const [colWidths, setColWidths] = usePersistedState<Record<string, number>>(
    columnWidthsKey(appLabel, modelName),
    {},
  );
  const resizeColumn = (key: string, width: number): void =>
    setColWidths((prev) => ({ ...prev, [key]: width }));

  // Column order (#218): persisted list of non-pk column names. The pk
  // stays pinned first (#360); new/unknown columns append in natural order.
  const [colOrder, setColOrder] = usePersistedState<string[]>(
    `dar:colorder:v1:${appLabel}:${modelName}`,
    [],
  );
  const [dragCol, setDragCol] = useState<string | null>(null);

  // Persist the applied list_filter selections per model (a UI
  // preference, like the column customizer) so a later bare visit can
  // restore them.
  const filtersStorageKey = filtersKey(appLabel, modelName);
  // Tracks the model whose saved filters have already been restored. Used
  // both to run restore once per model AND to gate the persist effect —
  // declared before persist because persist reads it.
  const restoredForModel = useRef<string>('');
  useEffect(() => {
    // Don't persist (or clear) until restore has run for this model. On a
    // bare-URL mount — e.g. returning from a detail page — activeFilters is
    // empty, so an ungated persist would removeItem() the saved filters
    // before the restore effect below could read them, wiping the view the
    // user expected to return to.
    if (restoredForModel.current !== `${appLabel}/${modelName}`) return;
    try {
      // Persist only real list_filter selections — never the
      // date_hierarchy drill (year/month/day), which shouldn't resurrect.
      const toPersist = Object.fromEntries(
        Object.entries(activeFilters).filter(([k]) => !DATE_PARAMS.has(k)),
      );
      if (Object.keys(toPersist).length > 0) {
        writeJSON(filtersStorageKey, toPersist);
      } else {
        // Clearing all filters clears the saved view — a later visit
        // shouldn't resurrect filters the user deliberately removed.
        removeKey(filtersStorageKey);
      }
    } catch {
      /* best effort */
    }
  }, [activeFilters, filtersStorageKey, appLabel, modelName]);

  // Restore filters from localStorage when arriving with a bare URL.
  // The URL is the source of truth at all times — this only hydrates
  // when there is nothing in the URL to honour, then writes the
  // restored filters straight back into the URL (replace) so refresh /
  // deep-link / share keep reflecting them. Runs once per model.
  useEffect(() => {
    const modelKey = `${appLabel}/${modelName}`;
    if (restoredForModel.current === modelKey) return;
    restoredForModel.current = modelKey;
    // Only hydrate a truly bare view (nothing but an optional `page`);
    // any q / filter / ordering means the URL is intentional — honour it.
    const onlyPage = Array.from(searchParams.keys()).every((k) => k === 'page');
    if (!onlyPage) return;
    const saved = readJSON<Record<string, string> | null>(filtersStorageKey, null);
    if (!saved || Object.keys(saved).length === 0) return;
    const next = new URLSearchParams();
    for (const [key, value] of Object.entries(saved)) {
      if (typeof value === 'string' && value !== '') next.set(key, value);
    }
    if ([...next.keys()].length > 0) setSearchParams(next, { replace: true });
  }, [appLabel, modelName, searchParams, setSearchParams, filtersStorageKey]);

  function toggleColumn(name: string, visibleCount: number): void {
    setHiddenCols((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else if (visibleCount > 1) {
        // Keep at least one column visible — never let the operator
        // hide the entire table out from under themselves.
        next.add(name);
      }
      return next;
    });
  }

  // Debounced search: commit `q` to the URL ~300ms after the user
  // stops typing, so the list refetches without a keystroke flood
  // (#177 toolbar). Enter / blur still commit immediately below.
  useEffect(() => {
    const handle = setTimeout(() => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if ((next.get('q') ?? '') === searchDraft) return prev;
          if (searchDraft) next.set('q', searchDraft);
          else next.delete('q');
          next.delete('page');
          return next;
        },
        { replace: true },
      );
    }, 300);
    return () => clearTimeout(handle);
  }, [searchDraft, setSearchParams]);

  function patchParams(mutate: (next: URLSearchParams) => void): void {
    const next = new URLSearchParams(searchParams);
    mutate(next);
    next.delete('page'); // any search/filter change resets to page 1
    setSearchParams(next);
  }

  function commitSearch(): void {
    patchParams((next) => {
      if (searchDraft) next.set('q', searchDraft);
      else next.delete('q');
    });
  }

  function setFilter(name: string, value: string): void {
    patchParams((next) => {
      if (value === '') next.delete(name);
      else next.set(name, value);
    });
  }

  function setPage(nextPage: number): void {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete('page');
    else next.set('page', String(nextPage));
    setSearchParams(next);
  }

  // Click-to-sort (#195): the URL `ordering` param is the source of
  // truth (single column in v1). `-name` = name DESC, `name` = ASC.
  // Clicking a header cycles asc → desc → unsorted.
  function toggleSort(key: string): void {
    patchParams((next) => {
      const current = searchParams.get('ordering') ?? '';
      if (current === key)
        next.set('ordering', `-${key}`); // asc → desc
      else if (current === `-${key}`)
        next.delete('ordering'); // desc → off
      else next.set('ordering', key); // unsorted/other → asc
    });
  }

  function toggleRow(key: string | number): void {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll(checked: boolean, pageRows: ListRow[]): void {
    setSelected(() => (checked ? new Set(pageRows.map((r) => r.pk)) : new Set()));
  }

  // Dropdown click: actions that declare requires_confirmation open the
  // styled confirm modal (#206); the rest run immediately.
  function requestAction(action: ActionDescriptor): void {
    if (runningAction || selected.size === 0) return;
    setActionsOpen(false);
    if (action.requires_confirmation) {
      setPendingAction(action);
    } else {
      void performAction(action);
    }
  }

  async function performAction(action: ActionDescriptor): Promise<void> {
    const pks = Array.from(selected);
    if (pks.length === 0 || runningAction) return;
    setRunningAction(true);
    setPendingAction(null);
    const count = pks.length;
    try {
      // Run the action over the wire and stay in the SPA: the styled
      // confirm modal already replaced Django's intermediate
      // confirmation page (the request carries `confirmed`), so we
      // never follow a server-side redirect / full-page navigation.
      // Clear the selection and re-validate the list in place.
      const result = await client.runAction(appLabel, modelName, action.name, pks);
      setSelected(new Set());
      await refresh();
      // Prefer the action's own message_user output (#442); fall back to a
      // generic confirmation when the action queued nothing.
      const msgs = result.messages ?? [];
      if (msgs.length > 0) {
        for (const m of msgs) {
          if (m.level === 'error' || m.level === 'warning') toast.error(m.message);
          else if (m.level === 'info' || m.level === 'debug') toast.info(m.message);
          else toast.success(m.message);
        }
      } else {
        toast.success(`${action.label} — ${count} item${count === 1 ? '' : 's'}.`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Action failed.');
    } finally {
      setRunningAction(false);
    }
  }

  if (loading && !data) return <ListSkeleton />;
  if (error && !data) {
    return <EmptyState title="Couldn't load the list" description={error.message} />;
  }
  if (!data) return null;

  // Inline list_editable (#243): editable columns render a text input
  // bound to the pending-edits map; all edits submit together via the
  // bulk PATCH. The backend rolls the whole batch back if any row fails.
  const canEdit = data.permissions.change;
  const scalarStr = (v: ListRow['fields'][string] | undefined): string =>
    v == null || typeof v === 'object' ? '' : String(v);
  const setCell = (pk: string, field: string, value: string): void =>
    setEdits((prev) => ({ ...prev, [pk]: { ...prev[pk], [field]: value } }));
  const editCount = Object.keys(edits).length;

  async function saveEdits(): Promise<void> {
    const updates = Object.entries(edits).map(([pk, fields]) => ({ pk, fields }));
    if (updates.length === 0) return;
    setSavingEdits(true);
    try {
      const res = await client.bulkUpdate(appLabel, modelName, updates);
      if (res.summary.rejected > 0) {
        toast.error(`${res.summary.rejected} row(s) failed — nothing was saved.`);
      } else {
        toast.success(`Saved ${res.summary.accepted} row${res.summary.accepted === 1 ? '' : 's'}.`);
        setEdits({});
        await refresh();
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Bulk save failed.');
    } finally {
      setSavingEdits(false);
    }
  }

  // The primary-key column (when it's part of list_display) is pinned
  // first, can't be hidden, and never truncates — it's the row's
  // identity and must stay fully readable (#360). `data.pk_field` names
  // it; if it isn't displayed, there's nothing to pin.
  const pkField = data.pk_field;
  const isPkCol = (name: string): boolean => name === pkField;
  const pkCol = data.columns.find((c) => isPkCol(c.name));
  const nonPkDescriptors = data.columns.filter((c) => !isPkCol(c.name));
  // Apply the saved column order (#218): known names in saved order, then
  // any new/unsaved columns in their natural order.
  const byColName = new Map(nonPkDescriptors.map((c) => [c.name, c]));
  const orderedNonPk = [
    ...colOrder
      .map((n) => byColName.get(n))
      .filter((c): c is (typeof nonPkDescriptors)[number] => Boolean(c)),
    ...nonPkDescriptors.filter((c) => !colOrder.includes(c.name)),
  ];
  const orderedDescriptors = pkCol ? [pkCol, ...orderedNonPk] : orderedNonPk;

  // Reorder a non-pk column before `target`, persisting the full order.
  const moveColumn = (dragged: string, target: string): void => {
    const names = orderedNonPk.map((c) => c.name);
    const from = names.indexOf(dragged);
    const to = names.indexOf(target);
    if (from === -1 || to === -1 || from === to) return;
    const next = [...names];
    next.splice(from, 1);
    next.splice(to, 0, dragged);
    setColOrder(next);
  };

  const columns = orderedDescriptors
    // The pk column is never hidden, even if a stale preference lists it.
    .filter((c) => isPkCol(c.name) || !hiddenCols.has(c.name))
    .map((c) => ({
      key: c.name,
      header: c.label,
      sortable: c.sortable,
      noTruncate: isPkCol(c.name),
      render: (row: ListRow) => {
        if (c.editable && canEdit) {
          const pk = String(row.pk);
          const value = edits[pk]?.[c.name] ?? scalarStr(row.fields[c.name]);
          return (
            <input
              value={value}
              onChange={(e) => setCell(pk, c.name, e.target.value)}
              onClick={(e) => e.stopPropagation()}
              className="w-full rounded border border-gray-300 px-1.5 py-0.5 text-sm"
              aria-label={`${c.label} for row ${pk}`}
            />
          );
        }
        return <FieldValueView value={row.fields[c.name]} type={c.type} />;
      },
    }));
  const visibleColumnCount = columns.length;

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  // Object-count label, shown in the pagination row (#95): "N of M
  // objects" when a full_count differs (filtered/estimated), else
  // "N object(s)".
  const countLabel =
    data.full_count != null && data.full_count !== data.total
      ? `${data.total.toLocaleString()} of ${data.full_count.toLocaleString()} ${
          data.full_count === 1 ? 'object' : 'objects'
        }`
      : `${data.total.toLocaleString()} object${data.total === 1 ? '' : 's'}`;
  const filters = data.filters ?? [];
  // Count of list_filters currently applied (drives the empty-state copy).
  const activeFilterCount = filters.filter((f) => activeFilters[f.name]).length;
  const actions = data.actions ?? [];
  const canRunActions = actions.length > 0 && data.permissions.change;

  // Derive the active sort (single column in v1) from the URL. `sortKey`
  // is '' when unsorted (no column header matches it → no caret shown).
  const ordering = searchParams.get('ordering') ?? '';
  const sortKey = ordering.replace(/^-/, '');
  const sortDirection: 'asc' | 'desc' = ordering.startsWith('-') ? 'desc' : 'asc';

  const listTitle = data.verbose_name_plural
    ? capitalize(data.verbose_name_plural)
    : data.object_name || modelName;

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Breadcrumb
            items={[{ label: 'Home', to: '/' }, { label: listTitle }]}
            renderLink={(to, className, label) => (
              <Link to={to} className={className}>
                {label}
              </Link>
            )}
          />
          <h1 className="text-2xl font-semibold">{listTitle}</h1>
        </div>
        {/* Customize sits to the LEFT of the + Add button (#94). */}
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setColsOpen(true)}
            aria-haspopup="dialog"
            aria-label="Customize columns"
            title="Customize columns"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-gray-300 px-3 py-2 text-sm hover:bg-gray-100"
          >
            <Settings2 className="h-4 w-4" aria-hidden />
            Customize
            {hiddenCols.size > 0 && (
              <span className="ml-0.5 rounded-full bg-gray-500 px-1.5 py-0.5 text-xs text-white">
                {hiddenCols.size} hidden
              </span>
            )}
          </button>
          {data.permissions.add && (
            <Link
              to={withPreservedFilters(`/${appLabel}/${modelName}/add`, searchParams.toString())}
              className="rounded-md border border-primary bg-primary px-3 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              + Add {data.verbose_name ? capitalize(data.verbose_name) : modelName}
            </Link>
          )}
        </div>
      </header>

      {/* Search + inline per-filter dropdowns + toolbar actions, via the
          @dar/search FilterBar (replaces the old filter modal + chips). */}
      <FilterBar
        showSearch={data.search_fields.length > 0}
        searchValue={searchDraft}
        onSearchChange={setSearchDraft}
        onSearchCommit={commitSearch}
        searchHelpText={data.search_help_text}
        filters={filters}
        active={activeFilters}
        onFilterChange={setFilter}
        // Bulk-actions menu sits to the LEFT of the search input, and
        // only once at least one row is selected (Django changelist
        // parity — the actions selector leads the toolbar).
        leading={
          canRunActions && selected.size > 0 ? (
            <div className="relative">
              <button
                type="button"
                onClick={() => setActionsOpen((o) => !o)}
                aria-haspopup="menu"
                aria-expanded={actionsOpen}
                disabled={runningAction}
                className="shrink-0 rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100 disabled:opacity-50"
              >
                Actions · {selected.size} ▾
              </button>
              {actionsOpen && (
                <div
                  role="menu"
                  className="absolute left-0 z-20 mt-1 min-w-48 rounded border border-gray-200 bg-white py-1 shadow-lg"
                >
                  {actions.map((a) => (
                    <button
                      key={a.name}
                      type="button"
                      role="menuitem"
                      onClick={() => requestAction(a)}
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                      title={a.description}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : null
        }
        trailing={
          activeFilterCount > 0 ? (
            <button
              type="button"
              onClick={() => patchParams((next) => filters.forEach((f) => next.delete(f.name)))}
              title="Clear all filters"
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100"
            >
              <X className="h-4 w-4" aria-hidden />
              Clear all
            </button>
          ) : null
        }
      />

      {editCount > 0 && (
        <div className="flex items-center justify-between rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-sm text-blue-700">
          <span>
            {editCount} row{editCount === 1 ? '' : 's'} with unsaved edits.
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={savingEdits} onClick={() => setEdits({})}>
              Discard
            </Button>
            <Button variant="primary" disabled={savingEdits} onClick={() => void saveEdits()}>
              {savingEdits ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </div>
      )}

      {/* The list is a full-width table on desktop and stacked record-cards
          on narrow viewports (#421); both read from the same `columns`.
          Row checkboxes appear only when the model has bulk actions the
          user can run (#182). An empty list renders a proper empty-state
          with a "+ Add" call-to-action (#293) instead of a bare message,
          so a fresh model has an obvious next step.

          A foreground refetch (filter / search / sort / page change) keeps
          the previous `data` in hand; showing skeletons while `loading`
          makes the reload visible, and we only fall back to the
          empty-state when genuinely idle-and-empty, not mid-fetch. */}
      {!loading && data.results.length === 0 ? (
        <Card>
          <EmptyState
            title={q || activeFilterCount > 0 ? 'No matches' : 'No objects yet'}
            description={emptyLabel(Boolean(q), activeFilterCount)}
            action={
              data.permissions.add ? (
                <Link
                  to={withPreservedFilters(`/${appLabel}/${modelName}/add`, searchParams.toString())}
                  className="inline-flex shrink-0 rounded-md border border-blue-600 bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  + Add {data.verbose_name ? capitalize(data.verbose_name) : modelName}
                </Link>
              ) : undefined
            }
          />
        </Card>
      ) : isNarrow ? (
        // Stacked record-cards: the card list is its own bordered surface,
        // so it isn't wrapped in the table's <Card>. Inline list_editable
        // cells (the `columns` render functions) still work; sort / resize
        // are desktop-only affordances not surfaced on the cards.
        <RecordCardList
          columns={columns}
          rows={data.results}
          rowKey={(r) => r.pk}
          onRowClick={(row) =>
            navigate(
              withPreservedFilters(`/${appLabel}/${modelName}/${row.pk}`, searchParams.toString()),
            )
          }
          rowHref={(row) =>
            withPreservedFilters(
              `${hrefBase}/${appLabel}/${modelName}/${row.pk}`,
              searchParams.toString(),
            )
          }
          selectable={canRunActions}
          selectedKeys={selected}
          onToggleRow={toggleRow}
          loading={loading}
        />
      ) : (
        <Card>
          <Table
            columns={columns}
            rows={data.results}
            rowKey={(r) => r.pk}
            onRowClick={(row) =>
              navigate(
                withPreservedFilters(`/${appLabel}/${modelName}/${row.pk}`, searchParams.toString()),
              )
            }
            rowHref={(row) =>
              withPreservedFilters(
                `${hrefBase}/${appLabel}/${modelName}/${row.pk}`,
                searchParams.toString(),
              )
            }
            onSort={toggleSort}
            sortKey={sortKey}
            sortDirection={sortDirection}
            selectable={canRunActions}
            selectedKeys={selected}
            onToggleRow={toggleRow}
            onToggleAll={(checked) => toggleAll(checked, data.results)}
            loading={loading}
            columnWidths={colWidths}
            onColumnResize={resizeColumn}
          />
        </Card>
      )}
      <Pagination
        page={data.page}
        totalPages={totalPages}
        countLabel={countLabel}
        onChange={setPage}
      />

      {pendingAction && (
        <Modal
          title="Confirm action"
          onClose={() => setPendingAction(null)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setPendingAction(null)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => void performAction(pendingAction)}>
                Run
              </Button>
            </>
          }
        >
          <p className="text-sm text-gray-700">
            Run <span className="font-medium">{pendingAction.label}</span> on {selected.size}{' '}
            selected item{selected.size === 1 ? '' : 's'}?
          </p>
        </Modal>
      )}

      {colsOpen && (
        <Modal title="Layout" onClose={() => setColsOpen(false)}>
          <p className="mb-2 text-xs text-gray-500">Drag to reorder; toggle to show or hide.</p>
          <ul className="space-y-1">
            {orderedDescriptors.map((c) => {
              const pk = isPkCol(c.name);
              const visible = pk || !hiddenCols.has(c.name);
              // The pk column is always shown and can't be toggled; the
              // last remaining visible column also can't be hidden.
              const locked = pk || (visible && visibleColumnCount <= 1);
              return (
                <li
                  key={c.name}
                  draggable={!pk}
                  onDragStart={pk ? undefined : () => setDragCol(c.name)}
                  onDragEnd={() => setDragCol(null)}
                  onDragOver={pk ? undefined : (e) => e.preventDefault()}
                  onDrop={
                    pk
                      ? undefined
                      : (e) => {
                          e.preventDefault();
                          if (dragCol) moveColumn(dragCol, c.name);
                          setDragCol(null);
                        }
                  }
                  className={`flex items-center gap-2 rounded border border-transparent px-1 py-1 ${
                    pk ? '' : 'cursor-grab hover:border-gray-200'
                  } ${dragCol === c.name ? 'opacity-50' : ''}`}
                >
                  {pk ? (
                    <span className="w-4 shrink-0" aria-hidden />
                  ) : (
                    <GripVertical className="h-4 w-4 shrink-0 text-gray-400" aria-hidden />
                  )}
                  <label
                    className={`flex flex-1 items-center gap-2 text-sm ${
                      locked && !pk ? 'text-gray-400' : 'text-gray-800'
                    }`}
                  >
                    <Checkbox
                      checked={visible}
                      disabled={locked}
                      onChange={() => toggleColumn(c.name, visibleColumnCount)}
                    />
                    {c.label}
                  </label>
                </li>
              );
            })}
          </ul>
        </Modal>
      )}
    </div>
  );
}

function capitalize(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

// Empty-state copy. When a search / filter is active, say so; otherwise a
// plain "No objects yet." An active server-side default filter is surfaced
// by the Filter button + modal (see #283), not by over-explaining it here.
function emptyLabel(hasQuery: boolean, chipCount: number): string {
  if (hasQuery || chipCount > 0) return 'No results match the current search / filters.';
  return 'No objects yet.';
}
