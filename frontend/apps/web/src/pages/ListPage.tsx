// ListPage — paginated table view for one model.
//
// Reads from `useList` (in @dar/data), which talks to the list
// endpoint via @dar/api. Sorting, search, and pagination are
// controlled state local to this page; cache/network management is
// the data layer's job.

import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { useApiClient, useList, type ListRow, renderValue } from '@dar/data';
import { Card, EmptyState, Input, Spinner, Table } from '@dar/ui';

export function ListPage() {
  const params = useParams<{ appLabel: string; modelName: string }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const navigate = useNavigate();
  const client = useApiClient();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);

  const { data, loading, error } = useList({
    client,
    appLabel,
    modelName,
    q,
    page,
  });

  if (loading && !data) return <Spinner label="Loading…" />;
  if (error && !data) {
    return <EmptyState title="Couldn't load the list" description={error.message} />;
  }
  if (!data) return null;

  const columns = data.columns.map((c) => ({
    key: c.name,
    header: c.label,
    sortable: c.sortable,
    render: (row: ListRow) => renderValue(row.fields[c.name]),
  }));

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold capitalize">
            {appLabel} · {modelName}
          </h1>
          <p className="text-sm text-gray-500">
            {data.total.toLocaleString()} object{data.total === 1 ? '' : 's'}
          </p>
        </div>
        {data.search_fields.length > 0 && (
          <div className="w-64">
            <Input
              placeholder={`Search by ${data.search_fields.join(', ')}…`}
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </div>
        )}
      </header>

      <Card>
        <Table
          columns={columns}
          rows={data.results}
          rowKey={(r) => r.pk}
          onRowClick={(row) => navigate(`/${appLabel}/${modelName}/${row.pk}`)}
          emptyLabel={q ? 'No results match this search.' : 'No objects yet.'}
        />
      </Card>

      <Pagination page={data.page} totalPages={totalPages} onChange={(next) => setPage(next)} />
    </div>
  );
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
