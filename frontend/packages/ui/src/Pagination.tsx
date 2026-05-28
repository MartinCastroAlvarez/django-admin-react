// Pagination — generic prev/next pager. Props-driven, no business
// knowledge (CLAUDE.md §7): the caller owns the page state and supplies
// the bounds. Extracted from the ListPage god-component (#428).

export interface PaginationProps {
  page: number;
  totalPages: number;
  onChange: (next: number) => void;
  /**
   * Optional leading label (e.g. "1,234 objects", #95) shown before the
   * page indicator, separated by a middot. Omit for a bare pager.
   */
  countLabel?: string;
  /** Extra classes for the wrapping `<nav>` so callers can adjust spacing. */
  className?: string;
}

export function Pagination({
  page,
  totalPages,
  onChange,
  countLabel,
  className = '',
}: PaginationProps) {
  const prevDisabled = page <= 1;
  const nextDisabled = page >= totalPages;
  const buttonClass = (disabled: boolean): string =>
    // Give the enabled button an explicit border-gray-300 (matching the
    // Filter/Customize buttons): a bare `border` falls back to Tailwind's
    // light-gray default, which the dark-mode utility remap can't catch
    // and shows as a white border in dark mode.
    `px-3 py-1 rounded border ${
      disabled
        ? 'text-gray-300 border-gray-200 cursor-not-allowed'
        : 'border-gray-300 hover:bg-gray-100'
    }`;
  return (
    <nav className={`flex items-center justify-between text-sm text-gray-600 ${className}`}>
      <span>
        {countLabel != null && (
          <>
            {countLabel}
            {/* A vertically-centered middot separates the count from the
                page indicator (#95) — not a period. */}
            <span aria-hidden className="px-2 text-gray-400">
              ·
            </span>
          </>
        )}
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
