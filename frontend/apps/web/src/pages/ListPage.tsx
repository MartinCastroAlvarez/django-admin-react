// ListPage — paginated table view for one model.
//
// Reads from `useList` (in @dar/data), which talks to the list
// endpoint via @dar/api. Sorting, search, and pagination are
// controlled state local to this page; cache/network management is
// the data layer's job.

import { useEffect, useMemo, useState } from 'react';
import { ListFilter } from 'lucide-react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
  useApiClient,
  useList,
  type ActionDescriptor,
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

  async function runAction(action: ActionDescriptor): Promise<void> {
    const pks = Array.from(selected);
    if (pks.length === 0 || runningAction) return;
    if (
      action.requires_confirmation &&
      !window.confirm(`Run “${action.label}” on ${pks.length} selected item(s)?`)
    ) {
      return;
    }
    setRunningAction(true);
    setActionsOpen(false);
    try {
      const res = await client.runAction(appLabel, modelName, action.name, pks);
      if (res.redirect) {
        window.location.assign(res.redirect);
        return;
      }
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
  const canRunActions = actions.length > 0 && data.permissions.change;

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-4">
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
        {data.permissions.add && (
          <Link
            to={`/${appLabel}/${modelName}/add`}
            className="shrink-0 rounded-md border border-blue-600 bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Add{' '}
            {data.verbose_name ? capitalize(data.verbose_name) : modelName}
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
                    onClick={() => void runAction(a)}
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
          emptyLabel={q || chips.length ? 'No results match these filters.' : 'No objects yet.'}
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

// Modal on desktop, bottom-sheet on mobile. Closes on backdrop tap,
// the Done button, OR the Escape key.
function FilterModal({ filters, active, onChange, onClearAll, onClose }: FilterModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
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
