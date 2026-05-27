import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useSwrCache } from './swr-cache';

// Focus/poll revalidation is exercised separately; these isolate the
// core stale-while-revalidate contract by disabling the focus listener
// (and leaving the poll interval at its 0 default).
const opts = { refetchOnFocus: false as const };

beforeEach(() => {
  window.localStorage.clear();
});

describe('useSwrCache', () => {
  it('fetches on mount when there is no cached value', async () => {
    const fetcher = vi.fn().mockResolvedValue({ v: 'fresh' });
    const { result } = renderHook(() => useSwrCache({ cacheKey: 'k1', fetcher, ...opts }));

    // No cache → starts loading.
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.data).toEqual({ v: 'fresh' }));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('serves the cached value immediately, then revalidates to fresh', async () => {
    window.localStorage.setItem('k2', JSON.stringify({ v: 'cached' }));
    const fetcher = vi.fn().mockResolvedValue({ v: 'fresh' });
    const { result } = renderHook(() => useSwrCache({ cacheKey: 'k2', fetcher, ...opts }));

    // No spinner flash: data is present on the very first render (the
    // page renders a spinner only when `loading && !data`).
    expect(result.current.data).toEqual({ v: 'cached' });
    // Background revalidation then swaps in the canonical value.
    await waitFor(() => expect(result.current.data).toEqual({ v: 'fresh' }));
  });

  it('keeps the last cached value when the fetch fails (never blanks the view)', async () => {
    window.localStorage.setItem('k3', JSON.stringify({ v: 'cached' }));
    const fetcher = vi.fn().mockRejectedValue(new Error('boom'));
    const { result } = renderHook(() => useSwrCache({ cacheKey: 'k3', fetcher, ...opts }));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.data).toEqual({ v: 'cached' });
  });

  it('refresh() re-invokes the fetcher', async () => {
    const fetcher = vi.fn().mockResolvedValue({ v: 'x' });
    const { result } = renderHook(() => useSwrCache({ cacheKey: 'k4', fetcher, ...opts }));

    await waitFor(() => expect(result.current.data).toEqual({ v: 'x' }));
    await act(async () => {
      await result.current.refresh();
    });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('writes the fetched value into localStorage', async () => {
    const fetcher = vi.fn().mockResolvedValue({ v: 'persisted' });
    const { result } = renderHook(() => useSwrCache({ cacheKey: 'k5', fetcher, ...opts }));

    await waitFor(() => expect(result.current.data).toEqual({ v: 'persisted' }));
    const raw = window.localStorage.getItem('k5');
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw as string)).toEqual({ v: 'persisted' });
  });

  it('blanks to a loading state on a key change by default (#416)', async () => {
    // Detail-style: a new key with no cache must not keep the previous
    // record's data on screen — it would flash the wrong record.
    const fetcher = vi.fn().mockResolvedValue({ v: 'a' });
    const { result, rerender } = renderHook(
      ({ k }: { k: string }) => useSwrCache({ cacheKey: k, fetcher, ...opts }),
      { initialProps: { k: 'kc-a' } },
    );
    await waitFor(() => expect(result.current.data).toEqual({ v: 'a' }));

    fetcher.mockResolvedValueOnce({ v: 'b' });
    rerender({ k: 'kc-b' });
    // New uncached key → blanked + loading until the fetch lands.
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.data).toEqual({ v: 'b' }));
  });

  it('keeps the previous data on a key change when keepPreviousData is set (#368)', async () => {
    // List-style: a filter change (new key, no cache) keeps the prior
    // rows on screen and shows a foreground load, so the page chrome
    // stays put and only the table skeletons.
    const fetcher = vi.fn().mockResolvedValue({ v: 'page1' });
    const { result, rerender } = renderHook(
      ({ k }: { k: string }) =>
        useSwrCache({ cacheKey: k, fetcher, keepPreviousData: true, ...opts }),
      { initialProps: { k: 'kp-1' } },
    );
    await waitFor(() => expect(result.current.data).toEqual({ v: 'page1' }));

    fetcher.mockResolvedValueOnce({ v: 'page2' });
    rerender({ k: 'kp-2' });
    // Previous data retained (not blanked) while loading the new key.
    expect(result.current.data).toEqual({ v: 'page1' });
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.data).toEqual({ v: 'page2' }));
  });

  it('adopts the new key cached value immediately even with keepPreviousData', async () => {
    window.localStorage.setItem('kp-b', JSON.stringify({ v: 'cached-b' }));
    const fetcher = vi.fn().mockResolvedValue({ v: 'fresh-a' });
    const { result, rerender } = renderHook(
      ({ k }: { k: string }) =>
        useSwrCache({ cacheKey: k, fetcher, keepPreviousData: true, ...opts }),
      { initialProps: { k: 'kp-a' } },
    );
    await waitFor(() => expect(result.current.data).toEqual({ v: 'fresh-a' }));

    fetcher.mockResolvedValueOnce({ v: 'fresh-b' });
    rerender({ k: 'kp-b' });
    // The new key has a cache → show it at once (no stale-a, no blank),
    // then revalidate to the canonical value.
    expect(result.current.data).toEqual({ v: 'cached-b' });
    await waitFor(() => expect(result.current.data).toEqual({ v: 'fresh-b' }));
  });
});
