// Client-side cache purge — used on logout.
//
// The SPA persists server responses (registry, list rows, detail field
// values) plus per-model UI state (filters, visible columns) under the
// `dar:` localStorage namespace so views paint instantly from cache. On
// a shared / kiosk machine that data would otherwise survive a logout at
// rest, readable in DevTools by whoever sits down next. Django's own
// admin has no such exposure (it's server-rendered, nothing is cached
// client-side), so to match its security posture we wipe the namespace
// when the session ends.
//
// `dar:theme` is the one exception: it's a pure display preference (light
// / dark) with no session or data content, and keeping it across a logout
// is good single-user UX (you don't lose dark mode every time you sign
// out). Everything else — cached data AND per-model filter/column hints
// that reveal what the previous user was looking at — is purged.
//
// The namespace + the preserved-key set are owned by @dar/customization
// (the single source of truth for what's a UI preference), so adding a
// new "survives logout" preference there is enough — no edit here.

import { CUSTOMIZATION_NAMESPACE, PRESERVED_ON_LOGOUT } from '@dar/customization';

const PRESERVE = new Set<string>(PRESERVED_ON_LOGOUT);
const NAMESPACE = CUSTOMIZATION_NAMESPACE;

/**
 * Remove every `dar:`-prefixed localStorage entry except the preserved
 * display preferences. Safe to call when storage is unavailable
 * (SSR / privacy mode) — it degrades to a no-op.
 */
export function purgeLocalCache(): void {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    // Collect first: removing during iteration shifts the index.
    const doomed: string[] = [];
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith(NAMESPACE) && !PRESERVE.has(key)) {
        doomed.push(key);
      }
    }
    for (const key of doomed) window.localStorage.removeItem(key);
  } catch {
    // Storage disabled / quota errors — nothing we can do, and a failed
    // purge must never block the logout reload.
  }
}
