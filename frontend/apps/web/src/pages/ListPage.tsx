// ListPage — paginated table view for one model.
//
// Reads from `useList` (in @dar/data), which talks to the list
// endpoint via @dar/api. Sorting, search, and pagination are
// controlled state local to this page; cache/network management is
// the data layer's job.

import { useEffect, useMemo, useRef, useState } from 'react';
import { ListFilter, Settings2 } from 'lucide-react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  useApiClient,
  useList,
  type ActionDescriptor,
  type DateHierarchy,
  type FilterDescriptor,
  type FilterOption,
  type ListRow,
} from '@dar/data';
import { Breadcrumb, Button, Card, EmptyState, Input, Modal, Skeleton, Table } from '@dar/ui';
import { FieldValueView } from '@dar/details';

import { useToast } from '../toast';

// Query params the page manages itself; everything else is a
// `list_filter` key. `all` is Django's "Show all" flag (#385), not a
// filter, so it never becomes a chip or a persisted saved-view entry.
const RESERVED_PARAMS = new Set(['q', 'page', 'all']);

// `date_hierarchy` drill-down params (Django's standard year/month/day).
// They DO flow to the backend (as non-reserved params), but they're not
// `list_filter` keys: excluded from the persisted "saved view" so a date
// drill doesn't silently resurrect on a later bare visit.
const DATE_PARAMS = new Set(['year', 'month', 'day']);

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

export function ListPage() {
  const params = useParams<{ appLabel: string; modelName: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const navigate = useNavigate();
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
  // Filters live in a modal/bottom-sheet behind a button so they never
  // occupy fixed horizontal space on mobile or desktop (#177).
  const [filterOpen, setFilterOpen] = useState(false);
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
  // Column customizer (#196): hidden columns persist per app/model in
  // localStorage so the operator's layout survives reloads. UI-only
  // preference (not data) — keyed outside the `dar:v1:*` cache.
  const colsStorageKey = `dar:cols:${appLabel}:${modelName}`;
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(() => {
    try {
      const raw = localStorage.getItem(`dar:cols:${appLabel}:${modelName}`);
      return raw ? new Set(JSON.parse(raw) as string[]) : new Set();
    } catch {
      return new Set();
    }
  });
  const [colsOpen, setColsOpen] = useState(false);

  // Persist the applied list_filter selections per model (a UI
  // preference, like the column customizer) so a later bare visit can
  // restore them. Keyed outside the `dar:v1:*` data cache.
  const filtersStorageKey = `dar:filters:${appLabel}:${modelName}`;
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
        localStorage.setItem(filtersStorageKey, JSON.stringify(toPersist));
      } else {
        // Clearing all filters clears the saved view — a later visit
        // shouldn't resurrect filters the user deliberately removed.
        localStorage.removeItem(filtersStorageKey);
      }
    } catch {
      /* localStorage unavailable (private mode) — best effort. */
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
    let saved: Record<string, string> | null = null;
    try {
      const raw = localStorage.getItem(filtersStorageKey);
      saved = raw ? (JSON.parse(raw) as Record<string, string>) : null;
    } catch {
      saved = null;
    }
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
      try {
        localStorage.setItem(colsStorageKey, JSON.stringify([...next]));
      } catch {
        /* localStorage unavailable (private mode) — preference is best-effort. */
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

  // date_hierarchy drill (Django parity): set the URL to an exact
  // {year?, month?, day?} state, clearing any deeper levels. Reuses
  // patchParams so the page also resets to 1.
  function setDatePath(path: { year?: number | null; month?: number | null; day?: number | null }) {
    patchParams((next) => {
      for (const key of ['year', 'month', 'day'] as const) {
        const v = path[key];
        if (v === undefined || v === null) next.delete(key);
        else next.set(key, String(v));
      }
    });
  }

  function setPage(nextPage: number): void {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete('page');
    else next.set('page', String(nextPage));
    setSearchParams(next);
  }

  // "Show all N" / "Show paginated" (#385). Switching to show-all sets the
  // bare `?all` flag and drops the page param (show-all has no pages);
  // switching back removes it. Both keep the URL the source of truth so a
  // reload / share preserves the chosen mode.
  function setShowAll(enabled: boolean): void {
    const next = new URLSearchParams(searchParams);
    if (enabled) {
      next.set('all', '');
      next.delete('page');
    } else {
      next.delete('all');
    }
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
      await client.runAction(appLabel, modelName, action.name, pks);
      setSelected(new Set());
      await refresh();
      toast.success(`${action.label} — ${count} item${count === 1 ? '' : 's'}.`);
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
  const orderedDescriptors = pkCol
    ? [pkCol, ...data.columns.filter((c) => !isPkCol(c.name))]
    : data.columns;

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
        return <FieldValueView value={row.fields[c.name]} />;
      },
    }));
  const visibleColumnCount = columns.length;

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  // "Show all N" (#385): offer the control only when the list spans more
  // than one page AND the total is at/below the admin's
  // `list_max_show_all` cap — matching Django's changelist guard. When
  // show-all is active the backend returns every row on a single page, so
  // the Prev/Next pager is replaced by a "Show paginated" toggle.
  const canShowAll = !showAll && data.total > data.page_size && data.total <= data.list_max_show_all;
  const filters = data.filters ?? [];
  const hasFilters = filters.length > 0;
  const chips = buildChips(filters, activeFilters);
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
          <p className="text-sm text-gray-500">
            {data.full_count != null && data.full_count !== data.total
              ? `${data.total.toLocaleString()} of ${data.full_count.toLocaleString()} ${
                  data.full_count === 1 ? 'object' : 'objects'
                }`
              : `${data.total.toLocaleString()} object${data.total === 1 ? '' : 's'}`}
          </p>
        </div>
        {data.permissions.add && (
          <Link
            to={`/${appLabel}/${modelName}/add`}
            className="shrink-0 rounded-md border border-blue-600 bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Add {data.verbose_name ? capitalize(data.verbose_name) : modelName}
          </Link>
        )}
      </header>

      {data.date_hierarchy && (
        <DateHierarchyBar dh={data.date_hierarchy} onNavigate={setDatePath} />
      )}

      {/* Toolbar row (#177 / #182): Actions dropdown (only when rows are
          selected) + a left-aligned debounced search + the Filter
          button that opens the modal. */}
      <div className="flex flex-wrap items-center gap-2">
        {canRunActions && selected.size > 0 && (
          <div className="relative">
            <button
              type="button"
              onClick={() => setActionsOpen((o) => !o)}
              aria-haspopup="menu"
              aria-expanded={actionsOpen}
              disabled={runningAction}
              className="shrink-0 rounded border border-gray-300 px-3 py-2 text-sm hover:bg-gray-100 disabled:opacity-50"
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
        )}
        {data.search_fields.length > 0 && (
          <form
            className="w-72 max-w-full"
            onSubmit={(e) => {
              e.preventDefault();
              commitSearch();
            }}
          >
            <Input
              placeholder="Search…"
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              onBlur={commitSearch}
            />
          </form>
        )}
        {hasFilters && (
          <button
            type="button"
            onClick={() => setFilterOpen(true)}
            aria-haspopup="dialog"
            className="inline-flex shrink-0 items-center gap-1.5 rounded border border-gray-300 px-3 py-2 text-sm hover:bg-gray-100"
          >
            <ListFilter className="h-4 w-4" aria-hidden />
            Filter
            {chips.length > 0 && (
              <span className="ml-0.5 rounded-full bg-blue-600 px-1.5 py-0.5 text-xs text-white">
                {chips.length}
              </span>
            )}
          </button>
        )}
        <button
          type="button"
          onClick={() => setColsOpen(true)}
          aria-haspopup="dialog"
          aria-label="Customize columns"
          title="Customize columns"
          className="inline-flex shrink-0 items-center gap-1.5 rounded border border-gray-300 px-3 py-2 text-sm hover:bg-gray-100"
        >
          <Settings2 className="h-4 w-4" aria-hidden />
          Customize
          {hiddenCols.size > 0 && (
            <span className="ml-0.5 rounded-full bg-gray-500 px-1.5 py-0.5 text-xs text-white">
              {hiddenCols.size} hidden
            </span>
          )}
        </button>
      </div>

      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {chips.map((chip) => (
            <button
              key={chip.name}
              type="button"
              onClick={() => setFilter(chip.name, '')}
              className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700 hover:bg-blue-100"
            >
              <span className="font-medium">{chip.filterLabel}:</span>
              <span>{chip.valueLabel}</span>
              <span aria-hidden className="ml-1 text-blue-400">
                ✕
              </span>
            </button>
          ))}
          {chips.length > 1 && (
            <button
              type="button"
              onClick={() => patchParams((next) => chips.forEach((c) => next.delete(c.name)))}
              className="rounded-full px-3 py-1 text-xs text-gray-500 hover:text-gray-800 hover:underline"
            >
              Clear all
            </button>
          )}
        </div>
      )}

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

      {/* Table is always full-width now — filters live in the modal.
          Row checkboxes appear only when the model has bulk actions
          the user can run (#182). An empty list renders a proper
          empty-state with a "+ Add" call-to-action (#293) instead of a
          bare message, so a fresh model has an obvious next step. */}
      <Card>
        {/* A foreground refetch (filter / search / sort / page change)
            keeps the previous `data` in hand, so without this the stale
            rows would just sit there with no sign anything is happening.
            Show skeleton rows while `loading` so the reload is visible —
            and only fall back to the empty-state when we're genuinely
            idle-and-empty, not mid-fetch. */}
        {!loading && data.results.length === 0 ? (
          <EmptyState
            title={q || chips.length > 0 ? 'No matches' : 'No objects yet'}
            description={emptyLabel(Boolean(q), chips.length)}
            action={
              data.permissions.add ? (
                <Link
                  to={`/${appLabel}/${modelName}/add`}
                  className="inline-flex shrink-0 rounded-md border border-blue-600 bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  + Add {data.verbose_name ? capitalize(data.verbose_name) : modelName}
                </Link>
              ) : undefined
            }
          />
        ) : (
          <Table
            columns={columns}
            rows={data.results}
            rowKey={(r) => r.pk}
            onRowClick={(row) => navigate(`/${appLabel}/${modelName}/${row.pk}`)}
            onSort={toggleSort}
            sortKey={sortKey}
            sortDirection={sortDirection}
            selectable={canRunActions}
            selectedKeys={selected}
            onToggleRow={toggleRow}
            onToggleAll={(checked) => toggleAll(checked, data.results)}
            loading={loading}
          />
        )}
      </Card>
      {showAll ? (
        // Show-all mode: every row is on the page, so there's nothing to
        // page through — offer a way back to the paginated view instead.
        <nav className="flex items-center justify-between text-sm text-gray-600">
          <span>Showing all {data.total.toLocaleString()}</span>
          <button
            type="button"
            onClick={() => setShowAll(false)}
            className="rounded border border-gray-300 px-3 py-1 hover:bg-gray-100"
          >
            Show paginated
          </button>
        </nav>
      ) : (
        <div className="space-y-2">
          <Pagination page={data.page} totalPages={totalPages} onChange={setPage} />
          {canShowAll && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setShowAll(true)}
                className="text-sm text-blue-600 hover:underline"
              >
                Show all {data.total.toLocaleString()}
              </button>
            </div>
          )}
        </div>
      )}

      {filterOpen && (
        <FilterModal
          filters={filters}
          active={activeFilters}
          onChange={setFilter}
          onClearAll={() => patchParams((next) => chips.forEach((c) => next.delete(c.name)))}
          onClose={() => setFilterOpen(false)}
        />
      )}

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
        <Modal
          title="Columns"
          onClose={() => setColsOpen(false)}
          footer={
            <Button variant="primary" onClick={() => setColsOpen(false)}>
              Done
            </Button>
          }
        >
          <p className="mb-3 text-sm text-gray-500">Show or hide list columns.</p>
          <ul className="space-y-2">
            {orderedDescriptors.map((c) => {
              const pk = isPkCol(c.name);
              const visible = pk || !hiddenCols.has(c.name);
              // The pk column is always shown and can't be toggled; the
              // last remaining visible column also can't be hidden.
              const locked = pk || (visible && visibleColumnCount <= 1);
              return (
                <li key={c.name}>
                  <label
                    className={`flex items-center gap-2 text-sm ${
                      locked && !pk ? 'text-gray-400' : 'text-gray-800'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={visible}
                      disabled={locked}
                      onChange={() => toggleColumn(c.name, visibleColumnCount)}
                    />
                    {c.label}
                    {pk && <span className="ml-auto text-xs text-gray-400">always shown</span>}
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

// First-paint skeleton: shown while the very first list load is in
// flight (no cached/stale data yet, so the columns aren't known). Mirrors
// the real layout — title + count, the toolbar row, then a card of rows —
// with a sensible default column count so the page has weight instead of
// a lone spinner. Once `data` exists, refetch loading is shown inline by
// the Table's own `loading` skeleton (which uses the real columns).
function ListSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true">
      <span role="status" className="sr-only">
        Loading…
      </span>
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-28" />
      </div>
      <Card>
        <div className="divide-y divide-gray-100">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3">
              {Array.from({ length: 5 }).map((__, j) => (
                <Skeleton key={j} className="h-4 flex-1" />
              ))}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// date_hierarchy drill-down bar (#304 — Django changelist parity). Reads
// `active` for the current drill path (breadcrumb, each crumb navigates
// up) and `buckets` for the next level's options (drill down). The
// backend caps the level by the field; clicking wires ?year/?month/?day.
function DateHierarchyBar({
  dh,
  onNavigate,
}: {
  dh: DateHierarchy;
  onNavigate: (path: { year?: number | null; month?: number | null; day?: number | null }) => void;
}) {
  const { active, buckets } = dh;
  const level: 'year' | 'month' | 'day' | 'done' =
    active.year == null
      ? 'year'
      : active.month == null
        ? 'month'
        : active.day == null
          ? 'day'
          : 'done';

  const bucketLabel = (v: number): string =>
    level === 'month' ? (MONTH_NAMES[v - 1] ?? String(v)) : String(v);

  const nextPath = (v: number) => {
    if (level === 'year') return { year: v };
    if (level === 'month') return { year: active.year, month: v };
    return { year: active.year, month: active.month, day: v };
  };

  const crumb = 'rounded px-1.5 py-0.5 text-blue-600 hover:bg-blue-50 hover:underline';

  return (
    <nav aria-label="Date hierarchy" className="flex flex-wrap items-center gap-3 text-sm">
      <div className="flex flex-wrap items-center gap-1 text-gray-500">
        <button type="button" className={crumb} onClick={() => onNavigate({})}>
          All dates
        </button>
        {active.year != null && (
          <>
            <span aria-hidden>/</span>
            <button
              type="button"
              className={crumb}
              onClick={() => onNavigate({ year: active.year })}
            >
              {active.year}
            </button>
          </>
        )}
        {active.month != null && (
          <>
            <span aria-hidden>/</span>
            <button
              type="button"
              className={crumb}
              onClick={() => onNavigate({ year: active.year, month: active.month })}
            >
              {MONTH_NAMES[active.month - 1] ?? active.month}
            </button>
          </>
        )}
        {active.day != null && (
          <>
            <span aria-hidden>/</span>
            <span className="px-1.5 py-0.5 font-medium text-gray-700">{active.day}</span>
          </>
        )}
      </div>
      {level !== 'done' && buckets.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {buckets.map((b) => (
            <button
              key={b.value}
              type="button"
              onClick={() => onNavigate(nextPath(b.value))}
              className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 px-2.5 py-0.5 text-xs text-gray-700 hover:bg-gray-50"
            >
              {bucketLabel(b.value)}
              <span className="text-gray-400">{b.count}</span>
            </button>
          ))}
        </div>
      )}
    </nav>
  );
}

interface FilterModalProps {
  filters: FilterDescriptor[];
  active: Record<string, string>;
  onChange: (name: string, value: string) => void;
  onClearAll: () => void;
  onClose: () => void;
}

// Filter modal — shares the generic @dar/ui `Modal` (overlay, card,
// Esc + backdrop close) with the action-confirm so both look identical
// (#206). Only the body (filter controls) + footer are bespoke.
function FilterModal({ filters, active, onChange, onClearAll, onClose }: FilterModalProps) {
  return (
    <Modal
      title="Filters"
      onClose={onClose}
      footer={
        <div className="flex w-full items-center justify-between">
          <button
            type="button"
            onClick={onClearAll}
            className="text-sm text-gray-500 underline hover:text-gray-700"
          >
            Clear all
          </button>
          <Button variant="primary" onClick={onClose}>
            Done
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {filters.map((f) => (
          <FilterControl
            key={f.name}
            filter={f}
            // Fall back to the descriptor's server-applied `selected` (a
            // SimpleListFilter default) when the URL carries no value, so
            // the control reflects the rows actually returned (#283).
            value={active[f.name] ?? (f.selected != null ? String(f.selected) : '')}
            onChange={(v) => onChange(f.name, v)}
          />
        ))}
      </div>
    </Modal>
  );
}

interface Chip {
  name: string;
  filterLabel: string;
  valueLabel: string;
}

function optionsFor(filter: FilterDescriptor): FilterOption[] {
  return filter.lookups ?? filter.choices ?? [];
}

function buildChips(filters: FilterDescriptor[], active: Record<string, string>): Chip[] {
  const byName = new Map(filters.map((f) => [f.name, f]));
  const chips: Chip[] = [];
  for (const [name, value] of Object.entries(active)) {
    const f = byName.get(name);
    if (!f) continue;
    const opt = optionsFor(f).find((o) => String(o.value) === value);
    chips.push({ name, filterLabel: f.label, valueLabel: opt?.label ?? value });
  }
  return chips;
}

interface FilterControlProps {
  filter: FilterDescriptor;
  value: string;
  onChange: (value: string) => void;
}

function FilterControl({ filter, value, onChange }: FilterControlProps) {
  const labelId = `dar-filter-${filter.name}`;

  if (filter.type === 'date') {
    return (
      <div>
        <label htmlFor={labelId} className="mb-1 block text-sm font-medium text-gray-700">
          {filter.label}
        </label>
        <input
          id={labelId}
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
        />
      </div>
    );
  }

  const options: FilterOption[] =
    filter.type === 'boolean'
      ? [
          { value: 'true', label: 'Yes' },
          { value: 'false', label: 'No' },
        ]
      : optionsFor(filter);

  return (
    <div>
      <label htmlFor={labelId} className="mb-1 block text-sm font-medium text-gray-700">
        {filter.label}
      </label>
      <select
        id={labelId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={String(o.value)} value={String(o.value)}>
            {o.label}
          </option>
        ))}
      </select>
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

interface PaginationProps {
  page: number;
  totalPages: number;
  onChange: (next: number) => void;
}

function Pagination({ page, totalPages, onChange }: PaginationProps) {
  const prevDisabled = page <= 1;
  const nextDisabled = page >= totalPages;
  const buttonClass = (disabled: boolean): string =>
    // Give the enabled button an explicit border-gray-300 (matching the
    // Filter/Customize buttons): a bare `border` falls back to Tailwind's
    // light-gray default, which the dark-mode utility remap can't catch
    // and shows as a white border in dark mode.
    `px-3 py-1 rounded border ${
      disabled
        ? 'text-gray-300 border-gray-200 cursor-not-allowed'
        : 'border-gray-300 hover:bg-gray-100'
    }`;
  return (
    <nav className="flex items-center justify-between text-sm text-gray-600">
      <span>
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className={buttonClass(prevDisabled)}
          disabled={prevDisabled}
          onClick={() => onChange(page - 1)}
        >
          ← Prev
        </button>
        <button
          type="button"
          className={buttonClass(nextDisabled)}
          disabled={nextDisabled}
          onClick={() => onChange(page + 1)}
        >
          Next →
        </button>
      </div>
    </nav>
  );
}
