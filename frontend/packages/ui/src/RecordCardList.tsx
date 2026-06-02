// RecordCardList — a stacked card layout for tabular data on narrow
// viewports (#421). It consumes the SAME `TableColumn<Row>[]` descriptors,
// rows, selection, and navigation props as `<Table>`, so a page defines
// its columns once and renders either layout from a single source. The
// first column is the record's identity (the card title); the rest become
// a label/value list. Generic and model-agnostic (CLAUDE.md §7).

import type { ReactNode } from 'react';

import { Checkbox } from './Checkbox';
import { Skeleton } from './Skeleton';
import type { TableColumn } from './Table';

export interface RecordCardListProps<Row> {
  /** Same column descriptors as `<Table>`; the first is the card title. */
  columns: TableColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string | number;
  /** Tap a card to open the record (in-app navigation). */
  onRowClick?: (row: Row) => void;
  /**
   * When set, the card title becomes a real `<a href>` so the browser's
   * native open-in-new-tab works (Cmd/Ctrl/middle-click); a plain tap is
   * intercepted for in-app nav via `onRowClick`. Mirrors `<Table>` (#253).
   * Should be the full app path including the router basename.
   */
  rowHref?: (row: Row) => string;
  /** Render a per-card selection checkbox wired to the props below. */
  selectable?: boolean;
  selectedKeys?: Set<string | number>;
  onToggleRow?: (key: string | number) => void;
  /** Show shimmer placeholder cards instead of `rows` during a refetch. */
  loading?: boolean;
  /** Placeholder card count while `loading` (defaults to a stable count). */
  skeletonRows?: number;
  emptyLabel?: string;
}

export function RecordCardList<Row>({
  columns,
  rows,
  rowKey,
  onRowClick,
  rowHref,
  selectable = false,
  selectedKeys,
  onToggleRow,
  loading = false,
  skeletonRows,
  emptyLabel = 'No results.',
}: RecordCardListProps<Row>) {
  // Only fall back to the empty-state when genuinely idle-and-empty — not
  // mid-fetch, where skeleton cards are shown instead (matches `<Table>`).
  if (!loading && rows.length === 0) {
    return <div className="py-8 text-center text-sm text-gray-500">{emptyLabel}</div>;
  }

  const selected = selectedKeys ?? new Set<string | number>();
  const skeletonCount = skeletonRows ?? Math.min(Math.max(rows.length || 6, 3), 12);
  // First column = identity → title; the rest become the label/value body.
  const [titleCol, ...detailCols] = columns;

  // list_display_links (#666): when the caller explicitly links NO column
  // (`list_display_links = None` → every column carries `isLink: false`),
  // the title is plain text and the card is not tappable — matching the
  // desktop `<Table>`. Otherwise behaviour is unchanged: the card is
  // tappable when `onRowClick` is set, and the title is an anchor when
  // `rowHref` is set (the legacy default of "first column = identity link").
  const anyExplicitLink = columns.some((c) => c.isLink !== undefined);
  const linksDisabled = anyExplicitLink && !columns.some((c) => c.isLink);
  const titleLinks = !linksDisabled;
  const cardNav = linksDisabled ? undefined : onRowClick;

  if (loading) {
    return (
      <ul className="space-y-2" aria-busy="true">
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <li key={`dar-card-skeleton-${i}`} className="rounded-lg border border-gray-300 bg-white p-4">
            <Skeleton className="mb-3 h-5 w-1/3" />
            <div className="space-y-2">
              {Array.from({ length: Math.max(detailCols.length, 2) }).map((__, j) => (
                <Skeleton key={j} className="h-4 w-2/3" />
              ))}
            </div>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <ul className="space-y-2">
      {rows.map((row) => {
        const key = rowKey(row);
        const isSelected = selected.has(key);
        const title: ReactNode = titleCol ? titleCol.render(row) : null;
        return (
          <li
            key={key}
            onClick={
              cardNav
                ? (e) => {
                    // A modified click (Cmd/Ctrl/Shift/Alt) is the browser's
                    // open-in-new-tab gesture — let the title anchor handle
                    // it; don't also navigate in-app.
                    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                    cardNav(row);
                  }
                : undefined
            }
            className={`rounded-lg border bg-white p-4 ${
              isSelected ? 'border-primary' : 'border-gray-300'
            } ${cardNav ? 'cursor-pointer hover:bg-gray-50' : ''}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1 font-medium text-gray-900">
                {titleLinks && titleCol && rowHref ? (
                  // Real anchor so native open-in-new-tab works; a plain
                  // left-click is intercepted for in-app nav (#253).
                  <a
                    href={rowHref(row)}
                    className="text-inherit no-underline hover:underline"
                    onClick={(e) => {
                      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                      e.preventDefault();
                      e.stopPropagation();
                      cardNav?.(row);
                    }}
                  >
                    {title}
                  </a>
                ) : (
                  title
                )}
              </div>
              {selectable && (
                // stopPropagation so toggling selection doesn't also open
                // the record (the card's onClick navigates).
                <span onClick={(e) => e.stopPropagation()} className="shrink-0">
                  <Checkbox
                    aria-label="Select row"
                    checked={isSelected}
                    onChange={() => onToggleRow?.(key)}
                  />
                </span>
              )}
            </div>
            {detailCols.length > 0 && (
              <dl className="mt-3 space-y-2 text-sm">
                {detailCols.map((col) => (
                  <div key={col.key}>
                    <dt className="text-xs uppercase tracking-wide text-gray-500">{col.header}</dt>
                    <dd className="mt-0.5 text-gray-700">{col.render(row)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </li>
        );
      })}
    </ul>
  );
}
