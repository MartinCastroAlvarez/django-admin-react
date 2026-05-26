// ListPage — paginated table view for one model.
//
// Reads from `useList` (in @dar/data), which talks to the list
// endpoint via @dar/api. Sorting, search, and pagination are
// controlled state local to this page; cache/network management is
// the data layer's job.

import { useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import {
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
        {data.search_fields.length > 0 && (
          <form
            className="w-64"
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

      <div className={hasFilters ? 'flex gap-4' : ''}>
        <div className="min-w-0 flex-1">
          <Card>
            <Table
              columns={columns}
              rows={data.results}
              rowKey={(r) => r.pk}
              onRowClick={(row) => navigate(`/${appLabel}/${modelName}/${row.pk}`)}
              emptyLabel={
                q || chips.length ? 'No results match these filters.' : 'No objects yet.'
              }
            />
          </Card>
          <div className="mt-4">
            <Pagination page={data.page} totalPages={totalPages} onChange={setPage} />
          </div>
        </div>

        {hasFilters && (
          <aside className="w-60 shrink-0">
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Filter
              </h2>
              <div className="space-y-4">
                {filters.map((f) => (
                  <FilterControl
                    key={f.name}
                    filter={f}
                    value={activeFilters[f.name] ?? ''}
                    onChange={(v) => setFilter(f.name, v)}
                  />
                ))}
              </div>
            </div>
          </aside>
        )}
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
