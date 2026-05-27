// Session helpers — the logout flow + client-cache purge.
//
// `@dar/data` owns the localStorage cache (CLAUDE.md §7), so the
// cache-purge-on-logout control lives here, not in a UI package.

import type { ApiClient } from '@dar/api';

// Every SPA cache key is namespaced under this prefix (see
// registry/list/detail contexts: `dar:registry:v1`, `dar:list:v1:…`,
// `dar:detail:v1:…`, `dar:cols:…`). Purging the prefix clears the lot.
const CACHE_PREFIX = 'dar:';

/**
 * Drop every client-side trace of the session: the `dar:*` localStorage
 * cache **and** the service worker's `dar:v1:*` caches (the SW's own
 * `dar:purge` message handler, #200/#208, does the deletion). Defense in
 * depth — reads are `Cache-Control: no-store` today, so there's normally
 * nothing cached, but this becomes load-bearing the moment a consumer
 * opts into a cacheable read policy (#225). Best-effort throughout:
 * private-mode / quota errors are swallowed.
 */
export function purgeClientCaches(): void {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const keys: string[] = [];
      for (let i = 0; i < window.localStorage.length; i += 1) {
        const key = window.localStorage.key(i);
        if (key && key.startsWith(CACHE_PREFIX)) keys.push(key);
      }
      for (const key of keys) window.localStorage.removeItem(key);
    } catch {
      /* private mode / quota — best-effort */
    }
  }
  if (typeof navigator !== 'undefined' && navigator.serviceWorker?.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'dar:purge' });
  }
}

/**
 * Log out: flush the session via the API, then purge all client-side
 * caches regardless of the request outcome — a network failure must not
 * leave stale cached data behind. After this resolves the caller should
 * re-validate auth (e.g. `useRegistry().refresh()`), which 403s and
 * surfaces the login screen.
 */
export async function logout(client: ApiClient): Promise<void> {
  try {
    await client.logout();
  } finally {
    purgeClientCaches();
  }
}
