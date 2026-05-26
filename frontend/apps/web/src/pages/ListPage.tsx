// ListPage — paginated table view for one model.
//
// Reads from `useList` (in @dar/data), which talks to the list
// endpoint via @dar/api. Sorting, search, and pagination are
// controlled state local to this page; cache/network management is
// the data layer's job.

import { useMemo, useState } from 'react';
import { ListFilter } from 'lucide-react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  runAction,
  useApiClient,
  useList,
  type FilterDescriptor,
  type FilterOption,
  type ListRow,
} from '@dar/data';
import { Card, EmptyState, Input, Spinner, Table } from '@dar/ui';

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

  const { data, loading, error } = useList({
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
  // Bulk-action row selection (#182). Holds the selected pks; the
  // action toolbar appears when ≥1 row is selected.
  const [selectedPks, setSelectedPks] = useState<Set<string | number>>(new Set());
  const [bulkAction, setBulkAction] = useState('');
  const [running, setRunning] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);

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

  if (loading && !data) return <Spinner label="Loading…" />;
  if (error && !data) {
    return <EmptyState title="Couldn't load the list" description={error.message} />;
  }
  if (!data) return null;

  const columns = data.columns.map((c) => ({
    key: c.name,
    header: c.label,
    sortable: c.sortable,
    render: (row: ListRow) => <FieldValueView value={row.fields[c.name]} />,
  }));

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const filters = data.filters ?? [];
  const hasFilters = filters.length > 0;
  const chips = buildChips(filters, activeFilters);
  const actions = data.actions ?? [];
  const rows = data.results;

  // --- bulk-action selection (#182) -------------------------------- //
  const allSelected = rows.length > 0 && rows.every((r) => selectedPks.has(r.pk));
  const someSelected = rows.some((r) => selectedPks.has(r.pk));
  function toggleRow(row: ListRow): void {
    setSelectedPks((prev) => {
      const next = new Set(prev);
      if (next.has(row.pk)) next.delete(row.pk);
      else next.add(row.pk);
      return next;
    });
  }
  function toggleAll(): void {
    setSelectedPks((prev) => {
      if (rows.every((r) => prev.has(r.pk))) {
        const next = new Set(prev);
        rows.forEach((r) => next.delete(r.pk));
        return next;
      }
      return new Set([...prev, ...rows.map((r) => r.pk)]);
    });
  }

  async function applyBulkAction(): Promise<void> {
    const descriptor = actions.find((a) => a.name === bulkAction);
    if (!descriptor || selectedPks.size === 0) return;
    if (
      descriptor.requires_confirmation &&
      !window.confirm(`Run "${descriptor.label}" on ${selectedPks.size} selected object(s)?`)
    ) {
      return;
    }
    setRunning(true);
    setBulkError(null);
    try {
      const result = await runAction({
        client,
        appLabel,
        modelName,
        actionName: bulkAction,
        pks: [...selectedPks],
        confirmed: true,
      });
      if (result.redirect) {
        window.location.href = result.redirect;
        return;
      }
      // Reload to reflect the action's effect (matches the admin's
      // post-action full reload). Clears selection implicitly.
      window.location.reload();
    } catch (e) {
      setBulkError(e instanceof Error ? e.message : 'The action failed.');
      setRunning(false);
    }
  }

  const selection = {
    isSelected: (row: ListRow) => selectedPks.has(row.pk),
    onToggle: toggleRow,
    allSelected,
    someSelected,
    onToggleAll: toggleAll,
  };

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            <span className="capitalize">{appLabel}</span> ·{' '}
            {data.verbose_name_plural
              ? capitalize(data.verbose_name_plural)
              : data.object_name || modelName}
          </h1>
          <p className="text-sm text-gray-500">
            {data.total.toLocaleString()} object{data.total === 1 ? '' : 's'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {data.search_fields.length > 0 && (
            <form
              className="w-56"
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
              Filters
              {chips.length > 0 && (
                <span className="ml-0.5 rounded-full bg-blue-600 px-1.5 py-0.5 text-xs text-white">
                  {chips.length}
                </span>
              )}
            </button>
          )}
        </div>
      </header>

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

      {/* Bulk-action toolbar — appears when rows are selected (#182). */}
      {actions.length > 0 && selectedPks.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded border border-gray-200 bg-gray-50 px-3 py-2">
          <span className="text-sm text-gray-600">{selectedPks.size} selected</span>
          <select
            value={bulkAction}
            onChange={(e) => setBulkAction(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
            aria-label="Bulk action"
          >
            <option value="">Action…</option>
            {actions.map((a) => (
              <option key={a.name} value={a.name}>
                {a.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!bulkAction || running}
            onClick={applyBulkAction}
            className="rounded bg-blue-600 px-3 py-1 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {running ? 'Running…' : 'Go'}
          </button>
          <button
            type="button"
            onClick={() => setSelectedPks(new Set())}
            className="text-sm text-gray-500 underline hover:text-gray-700"
          >
            Clear selection
          </button>
          {bulkError && <span className="text-sm text-red-600">{bulkError}</span>}
        </div>
      )}

      {/* Table is always full-width now — filters live in the modal. */}
      <Card>
        <Table
          columns={columns}
          rows={data.results}
          rowKey={(r) => r.pk}
          onRowClick={(row) => navigate(`/${appLabel}/${modelName}/${row.pk}`)}
          emptyLabel={q || chips.length ? 'No results match these filters.' : 'No objects yet.'}
          selection={actions.length > 0 ? selection : undefined}
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

// Modal on desktop, bottom-sheet on mobile. Closing on backdrop tap or
// the Done button; Escape handled by the parent page's listeners are
// not needed here because the backdrop already gives an obvious exit.
function FilterModal({ filters, active, onChange, onClearAll, onClose }: FilterModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label="Filters"
    >
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="relative z-10 max-h-[85vh] w-full overflow-y-auto rounded-t-xl bg-white p-5 shadow-xl sm:max-w-md sm:rounded-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Filters</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close filters"
            className="rounded p-1 text-gray-500 hover:bg-gray-100"
          >
            ✕
          </button>
        </div>
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
        <div className="mt-5 flex justify-between">
          <button
            type="button"
            onClick={onClearAll}
            className="text-sm text-gray-500 underline hover:text-gray-700"
          >
            Clear all
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Done
          </button>
        </div>
      </div>
    </div>
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
