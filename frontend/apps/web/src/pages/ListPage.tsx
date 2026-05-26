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
  type FilterDescriptor,
  type FilterOption,
  type ListRow,
} from '@dar/data';
import { Button, Card, EmptyState, Input, Modal, Spinner, Table } from '@dar/ui';

import { FieldValueView } from '../components/FieldValueView';

// Query params the page manages itself; everything else is a
// `list_filter` key.
const RESERVED_PARAMS = new Set(['q', 'page']);

export function ListPage() {
  const params = useParams<{ appLabel: string; modelName: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const navigate = useNavigate();
  const client = useApiClient();
  const [searchParams, setSearchParams] = useSearchParams();

  // Search, page, and filters all live in the URL so a reload restores
  // the exact view (ACCEPTANCE N-3). Filters are every non-reserved
  // query param, keyed by the descriptor `name`.
  const q = searchParams.get('q') ?? '';
  const page = Number(searchParams.get('page') ?? '1') || 1;

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
  useEffect(() => {
    try {
      if (Object.keys(activeFilters).length > 0) {
        localStorage.setItem(filtersStorageKey, JSON.stringify(activeFilters));
      } else {
        // Clearing all filters clears the saved view — a later visit
        // shouldn't resurrect filters the user deliberately removed.
        localStorage.removeItem(filtersStorageKey);
      }
    } catch {
      /* localStorage unavailable (private mode) — best effort. */
    }
  }, [activeFilters, filtersStorageKey]);

  // Restore filters from localStorage when arriving with a bare URL.
  // The URL is the source of truth at all times — this only hydrates
  // when there is nothing in the URL to honour, then writes the
  // restored filters straight back into the URL (replace) so refresh /
  // deep-link / share keep reflecting them. Runs once per model.
  const restoredForModel = useRef<string>('');
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
    try {
      // Run the action over the wire and stay in the SPA: the styled
      // confirm modal already replaced Django's intermediate
      // confirmation page (the request carries `confirmed`), so we
      // never follow a server-side redirect / full-page navigation.
      // Clear the selection and re-validate the list in place.
      await client.runAction(appLabel, modelName, action.name, pks);
      setSelected(new Set());
      await refresh();
    } finally {
      setRunningAction(false);
    }
  }

  if (loading && !data) return <Spinner label="Loading…" />;
  if (error && !data) {
    return <EmptyState title="Couldn't load the list" description={error.message} />;
  }
  if (!data) return null;

  const columns = data.columns
    .filter((c) => !hiddenCols.has(c.name))
    .map((c) => ({
      key: c.name,
      header: c.label,
      sortable: c.sortable,
      render: (row: ListRow) => <FieldValueView value={row.fields[c.name]} />,
    }));
  const visibleColumnCount = data.columns.length - hiddenCols.size;

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
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

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            {data.verbose_name_plural
              ? capitalize(data.verbose_name_plural)
              : data.object_name || modelName}
          </h1>
          <p className="text-sm text-gray-500">
            {data.total.toLocaleString()} object{data.total === 1 ? '' : 's'}
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
              placeholder={`Search by ${data.search_fields.join(', ')}…`}
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

      {/* Table is always full-width now — filters live in the modal.
          Row checkboxes appear only when the model has bulk actions
          the user can run (#182). */}
      <Card>
        <Table
          columns={columns}
          rows={data.results}
          rowKey={(r) => r.pk}
          onRowClick={(row) => navigate(`/${appLabel}/${modelName}/${row.pk}`)}
          onSort={toggleSort}
          sortKey={sortKey}
          sortDirection={sortDirection}
          emptyLabel={emptyLabel(Boolean(q), chips.length, hasFilters)}
          selectable={canRunActions}
          selectedKeys={selected}
          onToggleRow={toggleRow}
          onToggleAll={(checked) => toggleAll(checked, data.results)}
        />
      </Card>
      <Pagination page={data.page} totalPages={totalPages} onChange={setPage} />

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
            {data.columns.map((c) => {
              const visible = !hiddenCols.has(c.name);
              const isLastVisible = visible && visibleColumnCount <= 1;
              return (
                <li key={c.name}>
                  <label
                    className={`flex items-center gap-2 text-sm ${
                      isLastVisible ? 'text-gray-400' : 'text-gray-800'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={visible}
                      disabled={isLastVisible}
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
            value={active[f.name] ?? ''}
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

// Empty-state copy. When a search / filter is active, say so. When the
// list is empty with NO query applied but the model HAS filters, hint
// that a default server-side view may be hiding rows — a `ModelAdmin`
// often scopes `get_queryset` (e.g. hiding test/archived rows) so a
// row exists but isn't in the default list. This is the most common
// "I know there's data but the list is empty" confusion.
function emptyLabel(hasQuery: boolean, chipCount: number, hasFilters: boolean): string {
  if (hasQuery || chipCount > 0) return 'No results match the current search / filters.';
  if (hasFilters) {
    return 'No objects in the default view. This model has filters — some rows may be hidden by a default view (e.g. test or archived data). Open Filter to adjust.';
  }
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
    `px-3 py-1 rounded border ${
      disabled ? 'text-gray-300 border-gray-200 cursor-not-allowed' : 'hover:bg-gray-100'
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
