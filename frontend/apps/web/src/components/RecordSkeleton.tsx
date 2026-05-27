// First-paint skeleton for a single record (detail read view + create
// form). Mirrors the real layout — a title block, then cards of
// label/value rows — so the page has weight while the schema/object is
// in flight instead of a lone centered spinner (#231). Decorative; the
// wrapper owns aria-busy + an sr-only status for assistive tech.

import { Card, Skeleton } from '@dar/ui';

interface RecordSkeletonProps {
  /** How many card sections to mock (detail fieldsets / create fieldsets). */
  sections?: number;
  /** Rows per section. */
  rows?: number;
}

export function RecordSkeleton({ sections = 2, rows = 4 }: RecordSkeletonProps) {
  return (
    <div className="space-y-4" aria-busy="true">
      <span role="status" className="sr-only">
        Loading…
      </span>
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-7 w-64" />
      </div>
      {Array.from({ length: sections }).map((_, s) => (
        <Card key={s}>
          <div className="divide-y divide-gray-100">
            {Array.from({ length: rows }).map((__, r) => (
              <div key={r} className="grid grid-cols-3 gap-4 py-3">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="col-span-2 h-4 w-3/4" />
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
