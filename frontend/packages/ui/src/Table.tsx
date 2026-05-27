// Generic table primitive. Renders a typed column descriptor list and
// rows of arbitrary shape; consumers (page packages) pass the data and
// the cell-render function. No business knowledge.

import type { MouseEvent as ReactMouseEvent, ReactNode } from 'react';

import { Skeleton } from './Skeleton';

// Smallest a column can be dragged to — keeps a handle reachable.
const MIN_COL_WIDTH = 60;

export interface TableColumn<Row> {
  key: string;
  header: ReactNode;
  render: (row: Row) => ReactNode;
  sortable?: boolean;
  align?: 'left' | 'right' | 'center';
  /**
   * Opt out of the default per-cell truncation (max-width + ellipsis).
   * The cell still stays on one line (the table scrolls horizontally),
   * but its full value is shown — e.g. a primary-key column whose
   * identity must never be clipped.
   */
  noTruncate?: boolean;
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
  /**
   * Per-column pixel widths (keyed by `column.key`). When any are set the
   * table switches to fixed layout so the widths are honoured exactly;
   * unset columns share the remaining space. The consumer owns
   * persistence (e.g. localStorage per model) — the primitive stays
   * generic.
   */
  columnWidths?: Record<string, number>;
  /**
   * Enables drag-to-resize: a handle on each column's right edge reports
   * the new pixel width here (live, during the drag). Omit to disable
   * resizing entirely.
   */
  onColumnResize?: (key: string, width: number) => void;
  /**
   * When true, render shimmer placeholder rows instead of `rows` (e.g.
   * during a foreground refetch when stale rows are still in hand). The
   * header — derived from `columns` — stays put so the layout doesn't
   * jump between loading and loaded.
   */
  loading?: boolean;
  /**
   * How many skeleton rows to show while `loading`. Defaults to a
   * layout-stable count derived from the current `rows` length so the
   * table keeps roughly its prior height.
   */
  skeletonRows?: number;
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
  loading = false,
  skeletonRows,
  columnWidths,
  onColumnResize,
}: TableProps<Row>) {
  // Only fall back to the empty-state when we're genuinely empty — not
  // while a fetch is in flight, where we'd rather show skeleton rows.
  if (!loading && rows.length === 0) {
    return <div className="py-8 text-center text-sm text-gray-500">{emptyLabel}</div>;
  }
  const selected = selectedKeys ?? new Set<string | number>();
  const allSelected = !loading && rows.length > 0 && rows.every((r) => selected.has(rowKey(r)));
  const skeletonCount = skeletonRows ?? Math.min(Math.max(rows.length || 8, 3), 12);

  // Column resize (#218-adjacent): once any width is set we switch to
  // fixed layout so the px widths are honoured exactly. A drag on a
  // column's right-edge handle reports the live width via onColumnResize;
  // the consumer persists it. In fixed mode every cell truncates at its
  // column width (so the `noTruncate` opt-out only applies to the default
  // auto layout — when the user controls widths, they widen to see more).
  const hasWidths = columnWidths != null && Object.keys(columnWidths).length > 0;
  const resizable = onColumnResize != null;

  const startResize = (key: string, e: ReactMouseEvent): void => {
    e.preventDefault();
    e.stopPropagation();
    const th = (e.currentTarget as HTMLElement).closest('th');
    const startWidth = th?.offsetWidth ?? columnWidths?.[key] ?? 150;
    const startX = e.clientX;
    const prevUserSelect = document.body.style.userSelect;
    document.body.style.userSelect = 'none';
    const onMove = (ev: MouseEvent): void => {
      onColumnResize?.(key, Math.max(MIN_COL_WIDTH, Math.round(startWidth + (ev.clientX - startX))));
    };
    const onUp = (): void => {
      document.body.style.userSelect = prevUserSelect;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  return (
    <div className="overflow-x-auto" aria-busy={loading || undefined}>
      <table className={`min-w-full text-sm ${hasWidths ? 'table-fixed' : ''}`}>
        {hasWidths && (
          <colgroup>
            {selectable && <col style={{ width: '2.5rem' }} />}
            {columns.map((col) => (
              <col
                key={col.key}
                style={columnWidths?.[col.key] ? { width: `${columnWidths[col.key]}px` } : undefined}
              />
            ))}
          </colgroup>
        )}
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
                  // Keyboard-operable sort (#434): a sortable header is
                  // focusable (tabIndex 0), reports its state via aria-sort,
                  // and sorts on Enter / Space — not just a mouse click.
                  aria-sort={
                    sortable
                      ? sortKey === col.key
                        ? sortDirection === 'desc'
                          ? 'descending'
                          : 'ascending'
                        : 'none'
                      : undefined
                  }
                  tabIndex={sortable ? 0 : undefined}
                  className={`group relative ${hasWidths ? 'overflow-hidden' : 'whitespace-nowrap'} px-4 py-2 font-medium ${align} ${sortable ? 'cursor-pointer hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500' : ''}`}
                  onClick={sortable ? () => onSort(col.key) : undefined}
                  onKeyDown={
                    sortable
                      ? (e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onSort(col.key);
                          }
                        }
                      : undefined
                  }
                >
                  <span className={`inline-flex items-center gap-1 ${hasWidths ? 'max-w-full truncate' : ''}`}>
                    {col.header}
                    {sortable ? (
                      sortKey === col.key ? (
                        // Active sort: show the current direction.
                        <span aria-hidden>{sortDirection === 'desc' ? '▼' : '▲'}</span>
                      ) : (
                        // Hint sortability: a faint caret that fades in on
                        // hover so the operator sees the column is clickable.
                        <span
                          aria-hidden
                          className="text-gray-400 opacity-0 transition-opacity group-hover:opacity-100"
                        >
                          ▲
                        </span>
                      )
                    ) : null}
                  </span>
                  {resizable && (
                    // Drag handle on the right edge. stopPropagation keeps
                    // a resize from also triggering the column's sort.
                    <span
                      role="separator"
                      aria-orientation="vertical"
                      aria-label={`Resize column`}
                      onMouseDown={(e) => startResize(col.key, e)}
                      onClick={(e) => e.stopPropagation()}
                      className="absolute right-0 top-0 z-10 h-full w-1.5 cursor-col-resize select-none hover:bg-blue-400/60"
                    />
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {loading
            ? Array.from({ length: skeletonCount }).map((_, i) => (
                <tr key={`dar-skeleton-${i}`}>
                  {selectable && (
                    <td className="w-10 px-4 py-2">
                      <Skeleton className="h-4 w-4" />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td key={col.key} className={`px-4 py-2 ${ALIGN_CLASSES[col.align ?? 'left']}`}>
                      <Skeleton className="h-4 w-full max-w-[12rem]" />
                    </td>
                  ))}
                </tr>
              ))
            : rows.map((row) => {
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
                      <td
                        key={col.key}
                        className={`px-4 py-2 ${ALIGN_CLASSES[col.align ?? 'left']}`}
                      >
                        {/* Cap very wide cells and truncate with an
                        ellipsis so one long column doesn't dominate the
                        table; full value is on the detail page.
                        `truncate` carries whitespace-nowrap so values
                        never split mid-word. A `noTruncate` column (e.g.
                        the primary key) opts out: still one line, but the
                        whole value shows and the table scrolls instead. */}
                        <div
                          className={
                            hasWidths
                              ? 'truncate'
                              : col.noTruncate
                                ? 'whitespace-nowrap'
                                : 'max-w-[16rem] truncate'
                          }
                        >
                          {col.render(row)}
                        </div>
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
