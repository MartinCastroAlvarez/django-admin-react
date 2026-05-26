// Generic table primitive. Renders a typed column descriptor list and
// rows of arbitrary shape; consumers (page packages) pass the data and
// the cell-render function. No business knowledge.

import type { ReactNode } from 'react';

export interface TableColumn<Row> {
  key: string;
  header: ReactNode;
  render: (row: Row) => ReactNode;
  sortable?: boolean;
  align?: 'left' | 'right' | 'center';
}

export interface TableProps<Row> {
  columns: TableColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string | number;
  onSort?: (key: string) => void;
  sortKey?: string;
  sortDirection?: 'asc' | 'desc';
  onRowClick?: (row: Row) => void;
  emptyLabel?: string;
}

const ALIGN_CLASSES = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
};

export function Table<Row>({
  columns,
  rows,
  rowKey,
  onSort,
  sortKey,
  sortDirection,
  onRowClick,
  emptyLabel = 'No results.',
}: TableProps<Row>) {
  if (rows.length === 0) {
    return <div className="py-8 text-center text-sm text-gray-500">{emptyLabel}</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 text-gray-700">
          <tr>
            {columns.map((col) => {
              const align = ALIGN_CLASSES[col.align ?? 'left'];
              const sortable = col.sortable && onSort;
              return (
                <th
                  key={col.key}
                  scope="col"
                  className={`px-4 py-2 font-medium ${align} ${sortable ? 'cursor-pointer hover:bg-gray-100' : ''}`}
                  onClick={sortable ? () => onSort(col.key) : undefined}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {sortable && sortKey === col.key ? (
                      <span aria-hidden>{sortDirection === 'desc' ? '▼' : '▲'}</span>
                    ) : null}
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.map((row) => {
            const key = rowKey(row);
            return (
              <tr
                key={key}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}
              >
                {columns.map((col) => (
                  <td key={col.key} className={`px-4 py-2 ${ALIGN_CLASSES[col.align ?? 'left']}`}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
