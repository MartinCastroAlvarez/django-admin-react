import { useEffect, useRef, useState } from 'react';
import { Trash2 } from 'lucide-react';

import { type DeletePreviewResponse } from '@dar/data';
import { Button, Modal } from '@dar/ui';

interface DeleteButtonProps {
  label: string;
  loadPreview: () => Promise<DeletePreviewResponse>;
  onConfirm: () => Promise<void>;
}

/**
 * Delete affordance: a danger button that opens a confirm dialog (the
 * shared @dar/ui Modal). On open it fetches the cascade preview (#153 /
 * Django admin's delete-confirmation parity) so the operator sees what
 * else gets removed, what's PROTECT-blocked, and which extra delete
 * perms are missing BEFORE the single destructive click. The Delete
 * button is disabled while the preview says `can_delete: false`
 * (protected rows or missing perms). The preview fetch is best-effort:
 * if it fails, the dialog degrades to the plain confirm rather than
 * blocking a legitimate delete. While the DELETE is in flight the modal
 * can't be dismissed so it can't be double-fired.
 */
export function DeleteButton({ label, loadPreview, onConfirm }: DeleteButtonProps) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<DeletePreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Latest-ref so the fetch fires only when the modal *opens*, not on
  // every parent re-render (e.g. the background list/detail refetch).
  const loadRef = useRef(loadPreview);
  loadRef.current = loadPreview;

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    setPreviewLoading(true);
    loadRef
      .current()
      .then((p) => {
        if (!cancelled) setPreview(p);
      })
      .catch(() => {
        // Best-effort: a failed preview must not block a valid delete.
        if (!cancelled) setPreview(null);
      })
      .finally(() => {
        if (!cancelled) setPreviewLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const close = () => {
    if (busy) return;
    setOpen(false);
    setErr(null);
    setPreview(null);
  };

  // Block the destructive action only when the preview positively says
  // so — never when it's still loading or failed to load.
  const blocked = preview !== null && !preview.can_delete;

  return (
    <>
      <Button variant="danger" onClick={() => setOpen(true)}>
        <span className="inline-flex items-center gap-1.5">
          <Trash2 className="h-4 w-4" aria-hidden /> Delete
        </span>
      </Button>
      {open && (
        <Modal
          title="Delete object"
          onClose={close}
          footer={
            <>
              <Button variant="secondary" disabled={busy} onClick={close}>
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={busy || previewLoading || blocked}
                onClick={async () => {
                  setBusy(true);
                  setErr(null);
                  try {
                    await onConfirm();
                  } catch (e) {
                    setErr(e instanceof Error ? e.message : 'Delete failed.');
                    setBusy(false);
                  }
                }}
              >
                {busy ? 'Deleting…' : 'Delete'}
              </Button>
            </>
          }
        >
          <p className="text-sm text-gray-700">
            Are you sure you want to delete <span className="font-medium">“{label}”</span>? This
            action cannot be undone.
          </p>

          {previewLoading && (
            <p className="mt-3 text-sm text-gray-500">Checking what this affects…</p>
          )}

          {preview && preview.cascade.length > 0 && (
            <div className="mt-3 text-sm text-gray-700">
              <p className="font-medium">This will also delete:</p>
              <ul className="mt-1 list-disc pl-5">
                {preview.cascade.map((c) => (
                  <li key={c.model}>
                    {c.count} {c.model}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {preview && preview.protected.length > 0 && (
            <div className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              <p className="font-medium">Blocked — protected related objects:</p>
              <ul className="mt-1 list-disc pl-5">
                {preview.protected.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {preview && preview.perms_needed.length > 0 && (
            <div className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              You don’t have permission to delete: {preview.perms_needed.join(', ')}.
            </div>
          )}

          {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
        </Modal>
      )}
    </>
  );
}
