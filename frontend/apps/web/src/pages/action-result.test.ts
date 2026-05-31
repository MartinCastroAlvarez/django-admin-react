// Lock the bulk-action result handling (#250 / #442 / #632 / #644):
//
//   1. redirect → `openLink` opens new tab → info toast
//   2. redirect → `openLink` returns null (popup blocked) →
//      pendingRedirect banner, NOT silently swallowed
//   3. refresh always fires (BOTH redirect and no-redirect paths)
//   4. messages[] toasts by level (error/warning → red,
//      info/debug → blue, success → green)
//   5. No messages + no redirect → generic "<action> — N item(s)" toast
//   6. No messages + WITH redirect → no generic toast (the redirect's
//      destination surfaces the next-step UX)

import { describe, expect, it, vi } from 'vitest';

import type { ActionDescriptor, ActionRunResponse } from '@dar/data';

import { handleActionResult } from './action-result';

const action: ActionDescriptor = {
  name: 'export',
  label: 'Export selected',
  description: '',
  requires_confirmation: false,
};

function makeArgs(
  result: ActionRunResponse,
  overrides: { openReturns?: Window | null } = {},
) {
  const toast = {
    success: vi.fn<(m: string) => void>(),
    error: vi.fn<(m: string) => void>(),
    info: vi.fn<(m: string) => void>(),
  };
  const refresh = vi.fn<() => Promise<void>>(async () => {});
  // `openReturns` may be `null` (popup blocked); `??` would
  // coalesce a real null away, so check for `undefined` (omitted).
  const openLink = vi.fn<(url: string) => Window | null>(
    () => ('openReturns' in overrides ? overrides.openReturns! : ({} as Window)),
  );
  const onPopupBlocked = vi.fn<(info: { url: string; label: string }) => void>();
  return {
    args: { result, action, count: 3, toast, refresh, openLink, onPopupBlocked },
    toast,
    refresh,
    openLink,
    onPopupBlocked,
  };
}

describe('handleActionResult', () => {
  it('opens redirect in a new tab and shows an info toast', async () => {
    const { args, toast, openLink, onPopupBlocked } = makeArgs({
      executed: true,
      action: 'export',
      redirect: '/exports/build/?ids=1,2,3',
    });
    await handleActionResult(args);
    expect(openLink).toHaveBeenCalledWith('/exports/build/?ids=1,2,3');
    expect(toast.info).toHaveBeenCalledWith('Export selected opened in a new tab.');
    expect(onPopupBlocked).not.toHaveBeenCalled();
  });

  it('surfaces a pendingRedirect when window.open is suppressed (popup blocker)', async () => {
    const { args, toast, openLink, onPopupBlocked } = makeArgs(
      { executed: true, action: 'export', redirect: 'https://exports.example/123' },
      { openReturns: null },
    );
    await handleActionResult(args);
    expect(openLink).toHaveBeenCalledOnce();
    expect(onPopupBlocked).toHaveBeenCalledWith({
      url: 'https://exports.example/123',
      label: 'Export selected',
    });
    // Crucially: no info toast in this path — the URL would be lost
    // without the banner the caller renders from the pendingRedirect.
    expect(toast.info).not.toHaveBeenCalled();
  });

  it('refreshes the changelist on BOTH the redirect and no-redirect paths', async () => {
    const withRedirect = makeArgs({ executed: true, action: 'export', redirect: '/x/' });
    await handleActionResult(withRedirect.args);
    expect(withRedirect.refresh).toHaveBeenCalledOnce();

    const noRedirect = makeArgs({ executed: true, action: 'export' });
    await handleActionResult(noRedirect.args);
    expect(noRedirect.refresh).toHaveBeenCalledOnce();
  });

  it('toasts each messages[] entry by level (error → red, info → blue, success → green)', async () => {
    const { args, toast } = makeArgs({
      executed: true,
      action: 'export',
      messages: [
        { level: 'error', message: 'one failed' },
        { level: 'info', message: 'two queued' },
        { level: 'success', message: 'three done' },
      ],
    });
    await handleActionResult(args);
    expect(toast.error).toHaveBeenCalledWith('one failed');
    expect(toast.info).toHaveBeenCalledWith('two queued');
    expect(toast.success).toHaveBeenCalledWith('three done');
  });

  it('falls back to a generic success toast when no messages and no redirect', async () => {
    const { args, toast } = makeArgs({ executed: true, action: 'export' });
    await handleActionResult(args);
    expect(toast.success).toHaveBeenCalledWith('Export selected — 3 items.');
  });

  it('uses singular "item" when count is 1', async () => {
    const { args, toast } = makeArgs({ executed: true, action: 'export' });
    args.count = 1;
    await handleActionResult(args);
    expect(toast.success).toHaveBeenCalledWith('Export selected — 1 item.');
  });

  it('does NOT emit the generic toast when the action redirected (the destination shows the next-step UX)', async () => {
    const { args, toast } = makeArgs({
      executed: true,
      action: 'export',
      redirect: '/exports/build/',
    });
    await handleActionResult(args);
    // info toast for the new-tab open is fine; the generic
    // "— N item(s)" success toast must NOT fire.
    expect(toast.success).not.toHaveBeenCalled();
  });
});
