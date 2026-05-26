/* django-admin-react service worker (Issue #86).
 *
 * Hand-rolled — no Workbox (keeps the audited surface small + zero new
 * npm dep). Contract: docs/ux/pwa.md §2. Security-critical invariants,
 * each load-bearing:
 *
 *  - SCOPE: only intercept requests under the SPA mount. Sibling Django
 *    views (admin login, project pages) pass straight through.
 *  - NO-STORE: never cache a response whose Cache-Control says no-store.
 *    The package emits no-store on every API read, so those are never
 *    cached — which is the point (SECURITY.md §4.7).
 *  - MUTATION SAFETY: never cache or replay non-GET requests.
 *  - CACHE-ON-LOGOUT: a "dar:purge" message deletes every dar:v1:*
 *    cache so read-cached payloads can't outlive the session.
 *
 * `MOUNT` is injected server-side by ServiceWorkerView so the scope
 * check is exact for the consumer's chosen mount.
 */
'use strict';

const MOUNT = "{{ mount|escapejs }}";
const CACHE_PREFIX = 'dar:v1:';
const SHELL_CACHE = CACHE_PREFIX + 'shell';

// --- lifecycle ------------------------------------------------------------
self.addEventListener('install', (event) => {
  // No heavy precache: the shell assets are hash-named and cached on
  // first fetch (stale-while-revalidate below). Activate immediately.
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  // Claim open clients and drop any stale-versioned dar caches.
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => k.startsWith(CACHE_PREFIX) && k !== SHELL_CACHE)
          .map((k) => caches.delete(k)),
      );
      await self.clients.claim();
    })(),
  );
});

// --- cache purge on logout (contract §5) ----------------------------------
self.addEventListener('message', (event) => {
  // Origin check (CodeQL js/missing-origin-check): only honour messages
  // from our own origin — the SPA pages this worker controls. A
  // cross-origin frame must never be able to drive the cache. When the
  // message comes from a same-origin client, `event.origin` is our
  // origin; for some internal client.postMessage paths it can be the
  // empty string — both are accepted, anything else is dropped.
  if (event.origin && event.origin !== self.location.origin) {
    return;
  }
  if (event.data && event.data.type === 'dar:purge') {
    event.waitUntil(
      (async () => {
        const keys = await caches.keys();
        await Promise.all(
          keys.filter((k) => k.startsWith(CACHE_PREFIX)).map((k) => caches.delete(k)),
        );
      })(),
    );
  }
});

// --- fetch routing --------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // SCOPE guarantee: only handle same-origin requests under the mount.
  // Everything else passes through untouched.
  if (url.origin !== self.location.origin || !url.pathname.startsWith(MOUNT)) {
    return;
  }

  // MUTATION SAFETY: writes (POST/PATCH/DELETE/...) must hit the network
  // and are never cached or replayed.
  if (request.method !== 'GET') {
    return;
  }

  event.respondWith(handleGet(request, url));
});

async function handleGet(request, url) {
  const isApi = url.pathname.startsWith(MOUNT + 'api/v1/');
  if (isApi) {
    // Network-first; fall back to last-good cache only if one exists.
    // (Per contract, API reads are no-store, so the cache is normally
    // empty — this still degrades gracefully if a consumer ever opts
    // into a cacheable read policy.)
    return networkFirst(request);
  }
  // Shell + static assets: stale-while-revalidate.
  return staleWhileRevalidate(request);
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    await maybeCache(request, response);
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request);
  const network = fetch(request)
    .then((response) => {
      maybeCache(request, response);
      return response;
    })
    .catch(() => cached);
  return cached || network;
}

// Cache a response ONLY when its Cache-Control does not forbid it.
async function maybeCache(request, response) {
  if (!response || !response.ok || response.type === 'opaque') return;
  const cc = (response.headers.get('Cache-Control') || '').toLowerCase();
  // NO-STORE invariant: never persist a response the server marked
  // no-store (every API read in this package is no-store).
  if (cc.includes('no-store')) return;
  const cache = await caches.open(SHELL_CACHE);
  // Clone before the body is consumed by the caller.
  await cache.put(request, response.clone());
}
