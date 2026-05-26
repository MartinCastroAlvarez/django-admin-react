// Generic modal primitive: a translucent dark overlay + a centered
// card (desktop) / bottom-sheet (mobile). No business knowledge —
// callers pass the title, body, and optional footer. Closes on
// backdrop click and Escape. Shared by the filter modal, the
// bulk-action confirm, and the delete confirm (#206).

import { useEffect } from 'react';
import type { ReactNode } from 'react';

export interface ModalProps {
  /** Accessible dialog title; also rendered as the header. */
  title: ReactNode;
  /** Called on Escape, backdrop click, or the close button. */
  onClose: () => void;
  children: ReactNode;
  /** Optional footer (action buttons). Rendered below the body. */
  footer?: ReactNode;
}

export function Modal({ title, onClose, children, footer }: ModalProps) {
  // Escape closes — registered once while the modal is mounted.
  useEffect(() => {
    function onKey(e: KeyboardEvent): void {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center sm:items-center"
      role="dialog"
      aria-modal="true"
    >
      {/* Translucent dark overlay — backdrop click closes. */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div className="relative z-10 max-h-[85vh] w-full overflow-y-auto rounded-t-xl bg-white p-5 shadow-xl sm:max-w-md sm:rounded-xl">
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
        <div>{children}</div>
        {footer != null && <div className="mt-5 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
}
