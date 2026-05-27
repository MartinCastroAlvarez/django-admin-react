// useSwrCache — generic "stale-while-revalidate" hook backed by localStorage.
//
// Every data context in @dar/data (registry, list, detail) used to
// reimplement the same pattern: read cache → set state → fetch →
// overwrite. This hook lifts that pattern out so each context only
// owns its cache key and its fetch function.
//
// The contract:
//   1. First paint uses the cached value if any (sync, no flicker).
//   2. A background fetch runs in `useEffect` and updates state with
//      the canonical response.
//   3. `refresh()` re-fetches on demand (e.g. after a write).
//   4. The view stays live without a manual page reload: it
//      re-validates in the background when the tab regains focus
//      (`refetchOnFocus`, default on) and, when a caller opts in, on a
//      polling interval (`refetchInterval`). Background re-validation
//      does NOT toggle `loading`, so the on-screen value never flickers
//      to a spinner while the user is reading, and a failed poll keeps
//      the last good data instead of blanking the screen.
//
// Storage failures (private mode, quota exceeded) degrade silently:
// caching is an optimization, not a correctness layer.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export interface SwrState<T> {
  /** True while a network fetch is in flight and no cached value exists. */
  loading: boolean;
  /** Latest known value: cache first, then network. */
  data: T | null;
  /** Last error from `fetcher`, if any. */
  error: Error | null;
  /** Force a re-fetch (e.g. after a write). */
  refresh: () => Promise<void>;
}

export interface UseSwrCacheArgs<T> {
  /** localStorage key. Include version + identifying parameters. */
  cacheKey: string;
  /** Async function that returns the canonical value. */
  fetcher: () => Promise<T>;
  /** Dependencies that trigger a re-fetch when changed. */
  deps?: ReadonlyArray<unknown>;
  /**
   * Background poll cadence in ms. When > 0 the value is silently
   * re-fetched on this interval so the view tracks server-side changes
   * without a manual reload. `0` / omitted disables polling.
   */
  refetchInterval?: number;
  /**
   * Silently re-fetch when the tab/window regains focus or becomes
   * visible again. Default `true` — coming back to the admin shows
   * current data, not whatever was cached when you left.
   */
  refetchOnFocus?: boolean;
}

function readCache<T>(key: string): T | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeCache<T>(key: string, value: T | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Quota exceeded / privacy mode — degrade silently.
  }
}

export function useSwrCache<T>({
  cacheKey,
  fetcher,
  deps = [],
  refetchInterval = 0,
  refetchOnFocus = true,
}: UseSwrCacheArgs<T>): SwrState<T> {
  const cached = useMemo<T | null>(() => readCache<T>(cacheKey), [cacheKey]);
  const [data, setData] = useState<T | null>(cached);
  const [loading, setLoading] = useState<boolean>(cached === null);
  const [error, setError] = useState<Error | null>(null);

  // When the cache key changes (e.g. navigating from one object's detail
  // to a different object's), reset to the NEW key's cached value during
  // render. Otherwise `data` keeps the previous key's value — `useState`
  // initializers only run on mount — and the view shows stale content
  // until the background fetch lands (#416: detail→detail nav flashed the
  // prior record). Setting state during render is a supported React
  // pattern: it re-renders immediately, before paint, so no flicker.
  const keyRef = useRef(cacheKey);
  if (keyRef.current !== cacheKey) {
    keyRef.current = cacheKey;
    setData(cached);
    setLoading(cached === null);
    setError(null);
  }

  // Single fetch path. `showLoading` is true only for foreground
  // fetches (mount, deps change, explicit refresh) — background
  // re-validation passes false so it never flips the spinner on, and a
  // failed background fetch leaves the last good data on screen.
  const run = useCallback(
    async (showLoading: boolean) => {
      if (showLoading) setLoading(true);
      try {
        const next = await fetcher();
        setData(next);
        writeCache(cacheKey, next);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        if (showLoading) setLoading(false);
      }
    },
    // `fetcher` identity is the caller's responsibility (use useMemo).
    // We re-fetch when the cache key OR any caller dep changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cacheKey, ...deps],
  );

  const refresh = useCallback(() => run(true), [run]);

  // Stable handle to the latest background re-validation so the
  // interval / focus listeners don't have to re-subscribe whenever the
  // fetcher identity changes.
  const revalidate = useRef(() => run(false));
  revalidate.current = () => run(false);

  // Foreground fetch on mount and whenever the cache key / deps change.
  useEffect(() => {
    void run(true);
  }, [run]);

  // Background poll on the requested cadence.
  useEffect(() => {
    if (!refetchInterval || refetchInterval <= 0) return undefined;
    const id = window.setInterval(() => void revalidate.current(), refetchInterval);
    return () => window.clearInterval(id);
  }, [refetchInterval]);

  // Background re-validate when the tab regains focus / visibility.
  useEffect(() => {
    if (!refetchOnFocus || typeof window === 'undefined') return undefined;
    const onFocus = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
      void revalidate.current();
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onFocus);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onFocus);
    };
  }, [refetchOnFocus]);

  return useMemo(() => ({ loading, data, error, refresh }), [loading, data, error, refresh]);
}
