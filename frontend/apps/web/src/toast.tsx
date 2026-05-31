// Toast notifications (#289) — transient success/error/info feedback,
// the SPA equivalent of Django admin's "The X was added/changed/deleted
// successfully" messages. A small context provider + `useToast()` hook +
// a portal-rendered stack. Lives in apps/web (it owns app-level UI
// state); the visual chrome uses the same light utilities the rest of
// the shell does, so the index.css dark remap recolours it for free.

import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

type ToastKind = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}

/**
 * Dispatch a `message_user`-emitted message list to the toast API,
 * picking the colour per Django's level tag (#632 — list AND detail
 * page now share this; the detail page previously dropped the level
 * via the legacy `runObjectAction` adapter and toasted success-green
 * for every action even when the level was `error` / `warning`).
 *
 * Mirrors the legacy admin: `error` / `warning` → red, `info` /
 * `debug` → blue, `success` (and any unknown level) → green.
 */
export function toastMessages(
  toast: ToastApi,
  messages: ReadonlyArray<{ level: string; message: string }>,
): void {
  for (const m of messages) {
    if (m.level === 'error' || m.level === 'warning') toast.error(m.message);
    else if (m.level === 'info' || m.level === 'debug') toast.info(m.message);
    else toast.success(m.message);
  }
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const remove = useCallback((id: number) => {
    setToasts((ts) => ts.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (kind: ToastKind, message: string) => {
      const id = (idRef.current += 1);
      setToasts((ts) => [...ts, { id, kind, message }]);
      // Errors linger a little longer than confirmations.
      window.setTimeout(() => remove(id), kind === 'error' ? 6000 : 3500);
    },
    [remove],
  );

  const api = useMemo<ToastApi>(
    () => ({
      success: (m) => push('success', m),
      error: (m) => push('error', m),
      info: (m) => push('info', m),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <Toaster toasts={toasts} onDismiss={remove} />
    </ToastContext.Provider>
  );
}

const KIND_CLASS: Record<ToastKind, string> = {
  success: 'border-green-300 bg-green-50 text-green-700',
  error: 'border-red-300 bg-red-50 text-red-700',
  info: 'border-gray-300 bg-white text-gray-700',
};

function Toaster({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  if (typeof document === 'undefined' || toasts.length === 0) return null;
  return createPortal(
    <div
      className="fixed bottom-4 right-4 z-[200] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={`flex items-start gap-2 rounded-md border px-3 py-2 text-sm shadow-lg ${KIND_CLASS[t.kind]}`}
        >
          {t.kind === 'success' ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          ) : t.kind === 'error' ? (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          ) : (
            <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          )}
          <span className="flex-1">{t.message}</span>
          <button
            type="button"
            onClick={() => onDismiss(t.id)}
            aria-label="Dismiss notification"
            className="shrink-0 text-gray-400 hover:text-gray-600"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
      ))}
    </div>,
    document.body,
  );
}
