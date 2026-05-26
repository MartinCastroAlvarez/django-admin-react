// Modal — shared overlay dialog primitive.
//
// One translucent-overlay modal used across the SPA (filters,
// action-confirm, delete-confirm) so they all look the same. Generic +
// props-driven; no business knowledge. Mobile = bottom-sheet
// (`items-end`), desktop = centered. Closes on Escape, backdrop click,
// or the header close button.

import type { PropsWithChildren, ReactNode } from 'react';
import { useEffect } from 'react';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  /** Header title; when set, a header row with a close (✕) button renders. */
  title?: ReactNode;
  /** Footer node (typically the action buttons), right-aligned. */
  footer?: ReactNode;
  /** Accessible label when there's no visible `title`. */
  ariaLabel?: string;
}

export function Modal({
  open,
  onClose,
  title,
  footer,
  ariaLabel,
  children,
}: PropsWithChildren<ModalProps>) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-label={typeof title === 'string' ? title : ariaLabel}
    >
      {/* Translucent dark overlay — click to dismiss. */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="relative z-10 max-h-[85vh] w-full overflow-y-auto rounded-t-xl bg-white p-5 shadow-xl sm:max-w-md sm:rounded-xl">
        {title && (
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="rounded p-1 text-gray-500 hover:bg-gray-100"
            >
              ✕
            </button>
          </div>
        )}
        <div>{children}</div>
        {footer && <div className="mt-5 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}
