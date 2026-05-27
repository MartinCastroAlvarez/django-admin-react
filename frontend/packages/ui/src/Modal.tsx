// Generic modal primitive: a translucent dark overlay + a centered
// card (desktop) / bottom-sheet (mobile). No business knowledge —
// callers pass the title, body, and optional footer. Closes on
// backdrop click and Escape. Shared by the filter modal, the
// bulk-action confirm, and the delete confirm (#206).

import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
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
  const cardRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);
  const titleId = useId();

  // Escape closes — registered once while the modal is mounted.
  useEffect(() => {
    function onKey(e: KeyboardEvent): void {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  // Focus management (#292, a11y): on open, remember the triggering
  // element and move focus into the dialog; trap Tab within it; on
  // close, restore focus to the trigger so keyboard users aren't dumped
  // at the top of the page.
  useEffect(() => {
    previouslyFocused.current = (document.activeElement as HTMLElement | null) ?? null;
    const card = cardRef.current;
    card?.focus();

    function onKeyDown(e: KeyboardEvent): void {
      if (e.key !== 'Tab' || !card) return;
      const focusables = card.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (!first || !last) return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    card?.addEventListener('keydown', onKeyDown);
    return () => {
      card?.removeEventListener('keydown', onKeyDown);
      previouslyFocused.current?.focus?.();
    };
  }, []);

  // SSR / no-DOM guard — render nothing rather than crash.
  if (typeof document === 'undefined') return null;

  // Portal to <body> so the overlay always covers the true viewport.
  // Rendered inline, the modal lived inside <main>; an ancestor in the
  // layout (the sidebar <aside> uses `transform`, and the shell sets up
  // its own stacking contexts) trapped `position: fixed` so the overlay
  // only dimmed part of the page and painted *under* the sidebar. A
  // body portal escapes every ancestor stacking/containing context;
  // `z-[100]` keeps it above the sidebar's `z-50`.
  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-end justify-center sm:items-center">
      {/* Translucent dark overlay — backdrop click closes. */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div
        ref={cardRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative z-10 max-h-[85vh] w-full overflow-y-auto rounded-t-xl bg-white p-5 shadow-xl outline-none sm:max-w-md sm:rounded-xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 id={titleId} className="text-lg font-semibold">
            {title}
          </h2>
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
    </div>,
    document.body,
  );
}
