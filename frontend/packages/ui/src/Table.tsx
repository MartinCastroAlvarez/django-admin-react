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
  /**
   * When set, a leading checkbox column is rendered. `selectedKeys`
   * holds the currently-selected row keys; `onToggleRow` toggles one
   * row and `onToggleAll` toggles every row on the page. Generic,
   * props-driven — no business knowledge in the primitive.
   */
  selectable?: boolean;
  selectedKeys?: Set<string | number>;
  onToggleRow?: (key: string | number) => void;
  onToggleAll?: (checked: boolean) => void;
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
  selectable = false,
  selectedKeys,
  onToggleRow,
  onToggleAll,
}: TableProps<Row>) {
  if (rows.length === 0) {
    return <div className="py-8 text-center text-sm text-gray-500">{emptyLabel}</div>;
  }
  const selected = selectedKeys ?? new Set<string | number>();
  const allSelected = rows.length > 0 && rows.every((r) => selected.has(rowKey(r)));
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 text-gray-700">
          <tr>
            {selectable && (
              <th scope="col" className="w-10 px-4 py-2">
                <input
                  type="checkbox"
                  aria-label="Select all rows on this page"
                  checked={allSelected}
                  onChange={(e) => onToggleAll?.(e.target.checked)}
                />
              </th>
            )}
            {columns.map((col) => {
              const align = ALIGN_CLASSES[col.align ?? 'left'];
              const sortable = col.sortable && onSort;
              return (
                <th
                  key={col.key}
                  scope="col"
                  className={`whitespace-nowrap px-4 py-2 font-medium ${align} ${sortable ? 'cursor-pointer hover:bg-gray-100' : ''}`}
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
                {selectable && (
                  <td className="w-10 px-4 py-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      aria-label="Select row"
                      checked={selected.has(key)}
                      onChange={() => onToggleRow?.(key)}
                    />
                  </td>
                )}
                {columns.map((col) => (
                  <td key={col.key} className={`px-4 py-2 ${ALIGN_CLASSES[col.align ?? 'left']}`}>
                    {/* Cap very wide cells (e.g. UUID `id` columns) and
                        truncate with an ellipsis so one long column
                        doesn't dominate the table; full value is on the
                        detail page. `truncate` carries whitespace-nowrap
                        so values still never split mid-word. */}
                    <div className="max-w-[16rem] truncate">{col.render(row)}</div>
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
