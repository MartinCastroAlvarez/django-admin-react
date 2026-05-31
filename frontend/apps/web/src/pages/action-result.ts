// handleActionResult — what to do with the JSON envelope a
// changelist bulk-action returns (#250, #442, #632, #644). Pure
// function so the redirect / popup-blocked / messages flow is
// unit-testable without rendering the whole ListPage.
//
// Mirrors Django admin's `ModelAdmin.response_action` contract:
//
//   - An action that returns `HttpResponse` (typically a
//     `HttpResponseRedirect` to an intermediate / confirmation
//     page, an export wizard, a hijack flow) → the API surfaces
//     the `Location` as `result.redirect`. Open it in a NEW TAB
//     (`noopener,noreferrer`) so the changelist stays in view.
//   - Popup blocker eats `window.open` → return a
//     `{url, label}` pendingRedirect for the caller to render as a
//     clickable banner; the redirect must never be silently lost.
//   - Refresh the changelist on BOTH branches so any side-effects
//     the action had on the rows are visible.
//   - Messages with a `level` tag drive the toast colour (#632).
//   - When there are no messages AND no redirect, fall back to a
//     generic "<Action> — N item(s)." success toast — a redirect's
//     own destination usually surfaces next-step UX, no extra
//     "Done" toast needed for that path.

import type { ActionDescriptor, ActionRunResponse } from '@dar/data';

import type { ToastApi } from '../toast';
import { toastMessages } from '../toast';

export interface HandleActionResultArgs {
  result: ActionRunResponse;
  action: ActionDescriptor;
  count: number;
  toast: ToastApi;
  refresh: () => Promise<void>;
  /** Injected for testability. Production: `(url) =>
   *  window.open(url, '_blank', 'noopener,noreferrer')`. Returns
   *  `null` when the popup blocker suppresses the call. */
  openLink: (url: string) => Window | null;
  /** Called when `openLink` returns `null`. Caller renders a
   *  clickable fallback banner so the redirect URL isn't lost. */
  onPopupBlocked: (info: { url: string; label: string }) => void;
}

export async function handleActionResult(args: HandleActionResultArgs): Promise<void> {
  const { result, action, count, toast, refresh, openLink, onPopupBlocked } = args;
  if (result.redirect) {
    const opened = openLink(result.redirect);
    if (opened) {
      toast.info(`${action.label} opened in a new tab.`);
    } else {
      onPopupBlocked({ url: result.redirect, label: action.label });
    }
  }
  await refresh();
  const msgs = result.messages ?? [];
  if (msgs.length > 0) {
    toastMessages(toast, msgs);
  } else if (!result.redirect) {
    toast.success(`${action.label} — ${count} item${count === 1 ? '' : 's'}.`);
  }
}
