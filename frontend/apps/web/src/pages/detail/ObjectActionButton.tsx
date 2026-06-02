import { useState } from 'react';

import {
  ApiError,
  type ObjectActionDescriptor,
  type ObjectActionRunResponse,
} from '@dar/data';
import { Button } from '@dar/ui';

/**
 * One object-level change-page action button (#236). Disables + shows a
 * spinner while the POST is in flight; on success the parent re-fetches
 * the detail payload (so computed/readonly fields reflect the action) and
 * toasts, or navigates when the action returned a redirect. No full reload.
 */
export function ObjectActionButton({
  action,
  onRun,
  onSuccess,
  onError,
}: {
  action: ObjectActionDescriptor;
  onRun: () => Promise<ObjectActionRunResponse>;
  onSuccess: (result: ObjectActionRunResponse) => Promise<void> | void;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="secondary"
      loading={busy}
      disabled={busy}
      // Long action labels/descriptions (#672) wrap *inside* the button
      // (`whitespace-normal` + `break-words`) instead of forcing a wide
      // min-content box that would push the toolbar past the viewport.
      className="max-w-full whitespace-normal text-left break-words"
      title={action.description}
      onClick={async () => {
        setBusy(true);
        try {
          const result = await onRun();
          if (result.ok) {
            await onSuccess(result);
          } else {
            onError(result.message || 'The action could not be completed.');
          }
        } catch (err) {
          // A raising action callable comes back as a 400 (never a 500);
          // the client throws an ApiError. The 400 body is `{ok, error}`,
          // and the backend keeps that message generic on purpose, so we
          // surface a friendly fallback rather than the raw "HTTP 400".
          if (err instanceof ApiError) {
            const raw = err.envelope as unknown as { error?: unknown } | null;
            const detail =
              typeof raw?.error === 'string' ? raw.error : err.envelope?.error?.message;
            onError(detail || 'The action could not be completed.');
          } else {
            onError(err instanceof Error ? err.message : 'The action could not be completed.');
          }
        } finally {
          setBusy(false);
        }
      }}
    >
      {action.label}
    </Button>
  );
}
