import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

import { Card } from '@dar/ui';

/**
 * CollapsedEmptyInline (#591) — a slim card showing only the inline's
 * title + a caret toggle. The body (the "No X yet" copy + a hint to
 * enter edit mode) is hidden by default; clicking the title expands
 * it. Default-collapsed every page load — per-user persistence isn't
 * worth the storage for a detail-page hint.
 */
export function CollapsedEmptyInline({ label }: { label: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-left text-base font-semibold text-gray-900"
      >
        <span>{label}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open ? (
        <p className="mt-3 text-sm text-gray-500">
          No {label.toLowerCase()} yet. Click <span className="font-medium">Edit</span> to
          add the first one.
        </p>
      ) : null}
    </Card>
  );
}
