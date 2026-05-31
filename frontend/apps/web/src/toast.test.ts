// Lock the level → toast-method dispatch (#632). The detail page
// previously toasted success-green for every action, including
// `message_user(..., level=messages.ERROR)`, because the legacy
// `runObjectAction` adapter dropped the level field. This test
// pins the per-level routing so a regression turns red, not silent.
import { describe, expect, it, vi } from 'vitest';

import { toastMessages } from './toast';

function makeToast() {
  return {
    success: vi.fn<(message: string) => void>(),
    error: vi.fn<(message: string) => void>(),
    info: vi.fn<(message: string) => void>(),
  };
}

describe('toastMessages', () => {
  it('routes `error` to toast.error (red)', () => {
    const t = makeToast();
    toastMessages(t, [{ level: 'error', message: 'boom' }]);
    expect(t.error).toHaveBeenCalledWith('boom');
    expect(t.success).not.toHaveBeenCalled();
    expect(t.info).not.toHaveBeenCalled();
  });

  it('routes `warning` to toast.error (red — closest available)', () => {
    const t = makeToast();
    toastMessages(t, [{ level: 'warning', message: 'careful' }]);
    expect(t.error).toHaveBeenCalledWith('careful');
  });

  it('routes `info` to toast.info (blue)', () => {
    const t = makeToast();
    toastMessages(t, [{ level: 'info', message: 'fyi' }]);
    expect(t.info).toHaveBeenCalledWith('fyi');
  });

  it('routes `debug` to toast.info (blue)', () => {
    const t = makeToast();
    toastMessages(t, [{ level: 'debug', message: 'trace' }]);
    expect(t.info).toHaveBeenCalledWith('trace');
  });

  it('routes `success` (and unknown levels) to toast.success (green)', () => {
    const t = makeToast();
    toastMessages(t, [
      { level: 'success', message: 'ok' },
      { level: 'unknown', message: 'mystery' },
    ]);
    expect(t.success).toHaveBeenCalledWith('ok');
    expect(t.success).toHaveBeenCalledWith('mystery');
  });

  it('dispatches every entry in order — no merging, no dedupe', () => {
    const t = makeToast();
    toastMessages(t, [
      { level: 'error', message: 'first' },
      { level: 'success', message: 'second' },
      { level: 'error', message: 'third' },
    ]);
    expect(t.error).toHaveBeenCalledTimes(2);
    expect(t.error).toHaveBeenNthCalledWith(1, 'first');
    expect(t.error).toHaveBeenNthCalledWith(2, 'third');
    expect(t.success).toHaveBeenCalledWith('second');
  });
});
