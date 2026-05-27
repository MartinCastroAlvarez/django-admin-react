// useMediaQuery — subscribe to a CSS media query and re-render on change.
//
// Generic, model-agnostic (CLAUDE.md §7). Used to switch layouts at a
// breakpoint in JS when a pure-CSS toggle would force rendering both
// layouts into the DOM (e.g. the list's table vs. stacked record-cards,
// #421 — rendering only one avoids duplicate interactive controls).
//
// Built on `useSyncExternalStore` so the first render already reflects the
// real match (no post-mount flash) and React stays in sync with the
// `MediaQueryList` across resizes. Guards `window` / `matchMedia` so it is
// inert in any non-DOM environment.

import { useSyncExternalStore } from 'react';

const supported = (): boolean => typeof window !== 'undefined' && typeof window.matchMedia === 'function';

export function useMediaQuery(query: string): boolean {
  const subscribe = (onChange: () => void): (() => void) => {
    if (!supported()) return () => {};
    const mql = window.matchMedia(query);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  };
  const getSnapshot = (): boolean => (supported() ? window.matchMedia(query).matches : false);
  // No DOM on the server → report "doesn't match" so the wide (default)
  // layout renders; the client corrects on first paint via getSnapshot.
  const getServerSnapshot = (): boolean => false;
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
