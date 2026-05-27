// Theme (light / dark) preference + application (#84).
//
// The preference is a single localStorage key. Applying a theme toggles
// the `dark` class on <html>; the actual recolouring lives in the app's
// index.css as a scoped `.dark` utility remap (so existing light-utility
// components go dark without per-component `dark:` variants).
//
// `initTheme()` runs once, synchronously, before React mounts (see the
// app's main.tsx) so the correct theme is on the page at first paint —
// no flash from light to dark.

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'dar:theme';

/** The user's explicitly-chosen theme, or null if they never picked. */
export function getStoredTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === 'light' || value === 'dark' ? value : null;
  } catch {
    return null;
  }
}

/** The OS / browser preference, used as the default before any choice. */
export function systemTheme(): Theme {
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'light';
}

/** Effective theme: the saved choice if any, else the system default. */
export function resolveTheme(): Theme {
  return getStoredTheme() ?? systemTheme();
}

/** Reflect a theme onto the document (no persistence). */
export function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

/** Persist a chosen theme and apply it immediately. */
export function setTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* localStorage unavailable (private mode) — apply for this session. */
  }
  applyTheme(theme);
}

/** Apply the effective theme. Call once before first paint. */
export function initTheme(): void {
  applyTheme(resolveTheme());
}
