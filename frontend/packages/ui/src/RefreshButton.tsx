// RefreshButton (#592) — shared "refetch this page's data" affordance
// for the list-page filter toolbar (between Reset and Customize) and
// the detail-page header (next to History / Edit / Delete).
//
// Same code-organization pattern as ResetButton (#590): generic icon-
// agnostic primitive in @dar/ui, callers pass the refetch closure
// they already hold (`useList().refresh`, `useDetail().refresh`, …).
// Both surfaces get the same visual contract — same border, same
// pending spin, same a11y behaviour — by construction.

import { cloneElement, isValidElement, useState, type ReactNode } from 'react';

export interface RefreshButtonProps {
  /** Refetch closure. The button shows a pending state while the
   *  promise is in flight; on resolve / reject the spinner stops. */
  onRefresh: () => Promise<void> | void;
  /** Visible tooltip (and aria-label, since the button is icon-only).
   *  Default "Refresh". */
  tooltip?: string;
  /** Leading icon. If it accepts `className` the button applies
   *  `animate-spin` while pending — the lucide convention. Pass
   *  `null` to opt out. */
  icon?: ReactNode;
  /** Extra classes — kept narrow so the visual contract stays uniform. */
  className?: string;
}

export function RefreshButton({
  onRefresh,
  tooltip = 'Refresh',
  icon = null,
  className,
}: RefreshButtonProps) {
  const [pending, setPending] = useState(false);

  async function run(): Promise<void> {
    if (pending) return;
    setPending(true);
    try {
      await onRefresh();
    } finally {
      setPending(false);
    }
  }

  // If the caller's icon is a valid element that accepts a `className`,
  // augment it with `animate-spin` during a pending promise.
  const renderedIcon =
    pending && isValidElement<{ className?: string }>(icon)
      ? cloneElement(icon, {
          className: `${icon.props.className ?? ''} animate-spin`.trim(),
        })
      : icon;

  return (
    <button
      type="button"
      onClick={() => {
        void run();
      }}
      disabled={pending}
      title={tooltip}
      aria-label={tooltip}
      className={[
        'inline-flex shrink-0 items-center justify-center rounded-md border border-gray-300 px-2 py-1.5 text-sm',
        pending
          ? 'cursor-wait text-gray-400'
          : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
        className ?? '',
      ].join(' ')}
    >
      {renderedIcon}
    </button>
  );
}
