import type { DateHierarchy } from '@dar/data';

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

export interface DateHierarchyBarProps {
  dh: DateHierarchy;
  onNavigate: (path: { year?: number | null; month?: number | null; day?: number | null }) => void;
}

// date_hierarchy drill-down bar (#304 — Django changelist parity). Reads
// `active` for the current drill path (breadcrumb, each crumb navigates
// up) and `buckets` for the next level's options (drill down). The
// backend caps the level by the field; clicking wires ?year/?month/?day.
export function DateHierarchyBar({ dh, onNavigate }: DateHierarchyBarProps) {
  const { active, buckets } = dh;
  const level: 'year' | 'month' | 'day' | 'done' =
    active.year == null
      ? 'year'
      : active.month == null
        ? 'month'
        : active.day == null
          ? 'day'
          : 'done';

  const bucketLabel = (v: number): string =>
    level === 'month' ? (MONTH_NAMES[v - 1] ?? String(v)) : String(v);

  const nextPath = (v: number) => {
    if (level === 'year') return { year: v };
    if (level === 'month') return { year: active.year, month: v };
    return { year: active.year, month: active.month, day: v };
  };

  const crumb = 'rounded px-1.5 py-0.5 text-primary hover:bg-blue-50 hover:underline';

  return (
    <nav aria-label="Date hierarchy" className="flex flex-wrap items-center gap-3 text-sm">
      <div className="flex flex-wrap items-center gap-1 text-gray-500">
        <button type="button" className={crumb} onClick={() => onNavigate({})}>
          All dates
        </button>
        {active.year != null && (
          <>
            <span aria-hidden>/</span>
            <button type="button" className={crumb} onClick={() => onNavigate({ year: active.year })}>
              {active.year}
            </button>
          </>
        )}
        {active.month != null && (
          <>
            <span aria-hidden>/</span>
            <button
              type="button"
              className={crumb}
              onClick={() => onNavigate({ year: active.year, month: active.month })}
            >
              {MONTH_NAMES[active.month - 1] ?? active.month}
            </button>
          </>
        )}
        {active.day != null && (
          <>
            <span aria-hidden>/</span>
            <span className="px-1.5 py-0.5 font-medium text-gray-700">{active.day}</span>
          </>
        )}
      </div>
      {level !== 'done' && buckets.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {buckets.map((b) => (
            <button
              key={b.value}
              type="button"
              onClick={() => onNavigate(nextPath(b.value))}
              className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 px-2.5 py-0.5 text-xs text-gray-700 hover:bg-gray-50"
            >
              {bucketLabel(b.value)}
              <span className="text-gray-400">{b.count}</span>
            </button>
          ))}
        </div>
      )}
    </nav>
  );
}
