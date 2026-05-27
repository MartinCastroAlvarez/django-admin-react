// Popover — a small panel anchored under a trigger, used for the inline
// filter dropdowns (and any other "click a button → panel below it" UI).
// Generic + presentational: the caller owns `open` and `onClose`; the
// panel closes on outside-click and Escape. No portal — it positions
// absolutely relative to the trigger, which is enough for toolbar
// dropdowns (the toolbar isn't inside an overflow-hidden scroller).

import { useEffect, useRef, type ReactNode } from 'react';

export interface PopoverProps {
  open: boolean;
  onClose: () => void;
  /** The always-rendered trigger (a button). */
  trigger: ReactNode;
  /** Panel content, rendered only while `open`. */
  children: ReactNode;
  /** Which edge of the trigger the panel aligns to. Default `left`. */
  align?: 'left' | 'right';
  /** Extra classes for the panel (e.g. a fixed width). */
  panelClassName?: string;
}

export function Popover({
  open,
  onClose,
  trigger,
  children,
  align = 'left',
  panelClassName = '',
}: PopoverProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e: MouseEvent): void => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  return (
    <div ref={ref} className="relative inline-block">
      {trigger}
      {open && (
        <div
          role="dialog"
          className={`absolute z-30 mt-1 rounded-md border border-gray-200 bg-white shadow-lg ${
            align === 'right' ? 'right-0' : 'left-0'
          } ${panelClassName}`}
        >
          {children}
        </div>
      )}
    </div>
  );
}
