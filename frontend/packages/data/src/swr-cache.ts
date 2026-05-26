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
//
// Storage failures (private mode, quota exceeded) degrade silently:
// caching is an optimization, not a correctness layer.

import { useEffect, useMemo, useState } from 'react';

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

export function useSwrCache<T>({ cacheKey, fetcher, deps = [] }: UseSwrCacheArgs<T>): SwrState<T> {
  const cached = useMemo<T | null>(() => readCache<T>(cacheKey), [cacheKey]);
  const [data, setData] = useState<T | null>(cached);
  const [loading, setLoading] = useState<boolean>(cached === null);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useMemo(
    () => async () => {
      setLoading(true);
      setError(null);
      try {
        const next = await fetcher();
        setData(next);
        writeCache(cacheKey, next);
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setLoading(false);
      }
    },
    // `fetcher` identity is the caller's responsibility (use useMemo).
    // We re-fetch when the cache key OR any caller dep changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cacheKey, ...deps],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return useMemo(() => ({ loading, data, error, refresh }), [loading, data, error, refresh]);
}
