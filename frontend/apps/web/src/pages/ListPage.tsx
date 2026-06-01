// ListPage — paginated table view for one model.
//
// Reads from `useList` (in @dar/data), which talks to the list
// endpoint via @dar/api. Sorting, search, and pagination are
// controlled state local to this page; cache/network management is
// the data layer's job.

import { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { RefreshCw, Settings2, X } from 'lucide-react';
import { Link, useHref, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { useApiClient, useList, type ActionDescriptor, type ListRow } from '@dar/data';
import {
  columnsKey,
  lockedColsKey,
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
  EmptyState,
  Modal,
  Pagination,
  Popover,
  RecordCardList,
  RefreshButton,
  ResetButton,
  Table,
  useMediaQuery,
} from '@dar/ui';
import { FieldValueView } from '@dar/details';
import { ListSkeleton } from '@dar/list';
import { FilterBar } from '@dar/search';

import { useToast } from '../toast';
import { CHANGELIST_FILTERS_PARAM, withPreservedFilters } from '../changelistFilters';
import { handleActionResult } from './action-result';
import { capitalize, emptyLabel } from './list/helpers';

// Lazy-loaded so the @dnd-kit suite (the heaviest dep in this modal)
// only lands in the bundle of users who open the Customize modal
// (#586). Pages that never click "Customize" pay zero extra weight.
const ColumnLayoutModal = lazy(() => import('../ColumnLayoutModal'));

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
  // "Select all N matching" across pages (#386): when true the next action
  // runs over the whole filtered queryset, not just the page's `selected`.
  // Any manual selection change exits the mode.
  const [selectAcross, setSelectAcross] = useState(false);
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
  // Locked / frozen columns (#586 frozen-cols feature). PK is always
  // locked (never in the set); the set stores names of non-pk
  // columns the user has locked. Locked columns MUST form a
  // contiguous prefix from the pk — `<ColumnLayoutModal>` enforces
  // that invariant via its lockThrough / unlockFrom helpers.
  const [lockedCols, setLockedCols] = usePersistedSet(
    lockedColsKey(appLabel, modelName),
  );
  const [colsOpen, setColsOpen] = useState(false);
  // Popup-blocked fallback (#644). When an action returns a redirect
  // and `window.open` is suppressed by the browser's popup blocker
  // (the call isn't a direct user gesture by then — we're inside an
  // async handler after the POST resolves), surface a banner with a
  // clickable link so the redirect isn't silently swallowed.
  const [pendingRedirect, setPendingRedirect] = useState<{ url: string; label: string } | null>(
    null,
  );

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
    setSelectAcross(false);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll(checked: boolean, pageRows: ListRow[]): void {
    setSelectAcross(false);
    setSelected(() => (checked ? new Set(pageRows.map((r) => r.pk)) : new Set()));
  }

  // Dropdown click: actions that declare requires_confirmation open the
  // styled confirm modal (#206); the rest run immediately.
  function requestAction(action: ActionDescriptor): void {
    if (runningAction || (selected.size === 0 && !selectAcross)) return;
    setActionsOpen(false);
    if (action.requires_confirmation) {
      setPendingAction(action);
    } else {
      void performAction(action);
    }
  }

  async function performAction(action: ActionDescriptor): Promise<void> {
    if (runningAction || (selected.size === 0 && !selectAcross)) return;
    setRunningAction(true);
    setPendingAction(null);
    try {
      // "Select all N matching" (#386): pull every pk across pages from the
      // list endpoint (same q/filters, `all` — bounded by list_max_show_all,
      // the same guard as "Show all" #385), then run the action over them.
      // Otherwise act on the page-scoped selection. The styled confirm
      // modal already replaced Django's intermediate page, so we never
      // follow a server-side redirect.
      let pks: Array<string | number>;
      if (selectAcross) {
        const all = await client.list(appLabel, modelName, {
          all: true,
          filters: activeFilters,
          ...(q ? { q } : {}),
        });
        pks = all.results.map((r) => r.pk);
      } else {
        pks = Array.from(selected);
      }
      const count = pks.length;
      const result = await client.runAction(appLabel, modelName, action.name, pks);
      setSelected(new Set());
      setSelectAcross(false);
      // Per-result dispatch lives in `handleActionResult` so the
      // popup-blocked + refresh + level-toast flow is unit-testable
      // without rendering the whole page (#250, #442, #632, #644).
      await handleActionResult({
        result,
        action,
        count,
        toast,
        refresh,
        openLink: (url) => window.open(url, '_blank', 'noopener,noreferrer'),
        onPopupBlocked: (info) => setPendingRedirect(info),
      });
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
  // ColumnLayoutModal commits a reordered non-pk name array directly
  // via `setColOrder` — `arrayMove` from @dnd-kit/sortable handles the
  // splice logic. The hand-rolled `moveColumn` helper that used to
  // live here was retired in v1.3.0 along with the HTML5-DnD modal
  // it served (#586).

  const columns = orderedDescriptors
    // The pk column is never hidden, even if a stale preference lists it.
    .filter((c) => isPkCol(c.name) || !hiddenCols.has(c.name))
    .map((c) => ({
      key: c.name,
      header: c.label,
      sortable: c.sortable,
      noTruncate: isPkCol(c.name),
      // Frozen / sticky columns (#586): pk is implicitly always
      // locked + sticky; the user-locked set adds more. The Table
      // primitive measures pixel offsets after layout and writes
      // `style.left` so the sticky cluster stays pinned during
      // horizontal scroll. The mobile RecordCardList path renders
      // its own stacked layout (no horizontal scroll, no Table) so
      // this flag is a desktop/tablet-only concern by construction.
      sticky: isPkCol(c.name) || lockedCols.has(c.name),
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
  // Changelist actions = only those classified `batch` by the API
  // (api 1.0.6+ #603 revised). `detail`-target actions live on the
  // single-object page; rendering them here would let the operator
  // run a single-pk-shaped callable across a multi-row selection,
  // which would 400. Back-compat: pre-1.0.6 API omits `target`;
  // treat the absence as `batch` so older servers keep working.
  const actions = (data.actions ?? []).filter(
    (a) => a.target === undefined || a.target === 'batch',
  );
  const canRunActions = actions.length > 0 && data.permissions.change;

  // Select-all-across-pages (#386). The total matching the current filter
  // (full_count when show_full_result_count differs, else total).
  const matchingTotal = data.full_count ?? data.total;
  const allPageSelected =
    data.results.length > 0 && data.results.every((r) => selected.has(r.pk));
  // Offer "select all N matching" once the whole page is ticked AND there
  // are more rows than the page AND the total is within the bound we can
  // safely page through in one ?all request (the #385 "Show all" cap).
  const canOfferAcross =
    canRunActions &&
    allPageSelected &&
    !selectAcross &&
    matchingTotal > data.results.length &&
    matchingTotal <= data.list_max_show_all;
  // Rows the next action will run over — the whole filtered set when
  // "select across" is active, else the page-scoped selection.
  const effectiveCount = selectAcross ? matchingTotal : selected.size;

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
        {/* Header right-side toolbar (#608): one row holds every page-
            level affordance — Clear all (when filters are active),
            Refresh, Customize, then the primary `+ <Entity>` button.
            Previously these were split between the page header (Add)
            and the FilterBar trailing slot (Clear all / Refresh /
            Customize), which read as two toolbars; consolidating into
            one row matches the detail-page header layout (#572) and
            removes the second row of chrome.
            The `+ Add` label dropped the word "Add" — the leading `+`
            already signals "create", so "Add" was redundant (#608). */}
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {activeFilterCount > 0 ? (
            <ResetButton
              isDirty
              onReset={() =>
                patchParams((next) => filters.forEach((f) => next.delete(f.name)))
              }
              label="Clear all"
              icon={<X className="h-4 w-4" aria-hidden />}
              title="Clear all filters"
            />
          ) : null}
          <RefreshButton
            onRefresh={refresh}
            tooltip="Refresh"
            icon={<RefreshCw className="h-4 w-4" aria-hidden />}
          />
          <button
            type="button"
            onClick={() => setColsOpen(true)}
            aria-haspopup="dialog"
            aria-label="Customize columns"
            title={
              hiddenCols.size > 0
                ? `Customize columns (${hiddenCols.size} hidden)`
                : 'Customize columns'
            }
            className="inline-flex shrink-0 items-center justify-center rounded-md border border-gray-300 px-2 py-1.5 text-sm hover:bg-gray-100"
          >
            <Settings2 className="h-4 w-4" aria-hidden />
          </button>
          {data.permissions.add && (
            <Link
              to={withPreservedFilters(`/${appLabel}/${modelName}/add`, searchParams.toString())}
              className="rounded-md border border-primary bg-primary px-3 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              + {data.verbose_name ? capitalize(data.verbose_name) : modelName}
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
          canRunActions && (selected.size > 0 || selectAcross) ? (
            // Actions menu (#574 width / #575 outside-click): rendered
            // through the shared <Popover> so the menu inherits the
            // outside-click + Escape close behaviour from the same
            // primitive the sidebar identity dropdown uses (#578). Width
            // tracks the longest action label between sensible bounds —
            // `min-w-56` (224px) so short labels don't collapse the
            // menu, `max-w-md` (28rem / 448px) so a single ridiculously
            // long label doesn't blow it open. Items are `whitespace-
            // nowrap truncate` so a longer-than-max label gets `…` with
            // the full text reachable via the existing `title=` tooltip.
            <Popover
              open={actionsOpen}
              onClose={() => setActionsOpen(false)}
              align="left"
              panelClassName="min-w-56 max-w-md py-1"
              trigger={
                <button
                  type="button"
                  onClick={() => setActionsOpen((o) => !o)}
                  aria-haspopup="menu"
                  aria-expanded={actionsOpen}
                  disabled={runningAction}
                  className="shrink-0 rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100 disabled:opacity-50"
                >
                  Actions · {effectiveCount} ▾
                </button>
              }
            >
              <div role="menu">
                {actions.map((a) => (
                  <button
                    key={a.name}
                    type="button"
                    role="menuitem"
                    onClick={() => requestAction(a)}
                    className="block w-full truncate whitespace-nowrap px-3 py-2 text-left text-sm hover:bg-gray-100"
                    title={a.description ?? a.label}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </Popover>
          ) : null
        }
        // FilterBar's `trailing` slot retired in v1.4.5 / #608 — Clear
        // all / Refresh / Customize live in the page header now so the
        // SPA shows one toolbar per page, not two.
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

      {/* Popup-blocked fallback for an action redirect (#644). If
          window.open returns null (the browser suppressed the
          new-tab because we're past the direct-user-gesture moment),
          render a clickable link banner so the redirect URL isn't
          silently swallowed. The user opens it manually with a real
          click; dismiss closes the banner. Amber = "this needs your
          attention but it isn't an error." */}
      {pendingRedirect && (
        <div className="flex items-center justify-between rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <span>
            {pendingRedirect.label} wants to open a page —{' '}
            <a
              href={pendingRedirect.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium underline decoration-amber-500 underline-offset-2 hover:decoration-amber-700"
              onClick={() => setPendingRedirect(null)}
            >
              click to open in a new tab
            </a>
            .
          </span>
          <Button variant="secondary" onClick={() => setPendingRedirect(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Select-all-across-pages (#386). Once the whole page is ticked and
          more rows match, offer to extend the selection to the entire
          filtered set (Django changelist parity); while active, say so and
          offer to clear. Only when the total is within the safe ?all cap. */}
      {canOfferAcross || selectAcross ? (
        <div className="flex flex-wrap items-center justify-center gap-2 rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-center text-sm text-blue-700">
          {selectAcross ? (
            <>
              <span>All {matchingTotal.toLocaleString()} selected.</span>
              <button
                type="button"
                onClick={() => {
                  setSelectAcross(false);
                  setSelected(new Set());
                }}
                className="font-medium underline hover:no-underline"
              >
                Clear selection
              </button>
            </>
          ) : (
            <>
              <span>
                All {data.results.length} on this page {data.results.length === 1 ? 'is' : 'are'}{' '}
                selected.
              </span>
              <button
                type="button"
                onClick={() => setSelectAcross(true)}
                className="font-medium underline hover:no-underline"
              >
                Select all {matchingTotal.toLocaleString()} matching
              </button>
            </>
          )}
        </div>
      ) : null}

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
            Run <span className="font-medium">{pendingAction.label}</span> on {effectiveCount}{' '}
            selected item{effectiveCount === 1 ? '' : 's'}?
          </p>
        </Modal>
      )}

      {colsOpen && (
        <Suspense fallback={null}>
          <ColumnLayoutModal
            onClose={() => setColsOpen(false)}
            orderedDescriptors={orderedDescriptors}
            isPk={isPkCol}
            hiddenCols={hiddenCols}
            lockedCols={lockedCols}
            visibleColumnCount={visibleColumnCount}
            onToggle={toggleColumn}
            onReorder={setColOrder}
            onSetLocked={(next) => setLockedCols(() => next)}
            // The layout is "customised" when any preference has
            // state — saved order, hidden col, or locked col. All
            // three persist via localStorage; resetting drops them
            // back to empty so the ModelAdmin's registered defaults
            // take over again on the next render (#590).
            isCustomised={
              colOrder.length > 0 || hiddenCols.size > 0 || lockedCols.size > 0
            }
            onReset={() => {
              // `usePersistedSet`'s setter takes a functional updater,
              // not the raw next-value (unlike `useState`); returning a
              // fresh empty Set clears every saved entry. The
              // `colOrder` setter from `usePersistedState` is the
              // plain useState variant, so it accepts the raw next.
              setColOrder([]);
              setHiddenCols(() => new Set<string>());
              setLockedCols(() => new Set<string>());
            }}
          />
        </Suspense>
      )}
    </div>
  );
}
