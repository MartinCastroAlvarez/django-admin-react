// ListSkeleton — first-paint placeholder for the list page, shown while
// the very first load is in flight (no cached/stale data yet, so the real
// columns aren't known). Mirrors the real layout — title + count, the
// toolbar row, then a card of rows — so the page has weight instead of a
// lone spinner. Once data exists, refetch loading is shown inline by the
// Table's own `loading` skeleton (which uses the real columns).
//
// Extracted from the ListPage god-component (#428 / #303). Props let a
// caller tune the placeholder shape; the defaults match the prior inline
// layout.

import { Card, Skeleton } from '@dar/ui';

export interface ListSkeletonProps {
  /** Placeholder row count (default 8). */
  rows?: number;
  /** Placeholder cells per row (default 5). */
  columns?: number;
}

export function ListSkeleton({ rows = 8, columns = 5 }: ListSkeletonProps = {}) {
  return (
    <div className="space-y-4" aria-busy="true">
      <span role="status" className="sr-only">
        Loading…
      </span>
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-28" />
      </div>
      <Card>
        <div className="divide-y divide-gray-100">
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3">
              {Array.from({ length: columns }).map((__, j) => (
                <Skeleton key={j} className="h-4 flex-1" />
              ))}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
