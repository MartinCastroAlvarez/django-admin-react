// Theme (light / dark) preference + application (#84).
//
// The preference is the single `THEME_KEY` localStorage entry. Applying a
// theme toggles the `dark` class on <html>; the actual recolouring lives
// in the app's index.css as a scoped `.dark` utility remap (so existing
// light-utility components go dark without per-component `dark:` variants).
//
// `initTheme()` runs once, synchronously, before React mounts (see the
// app's main.tsx) so the correct theme is on the page at first paint — no
// flash from light to dark.

import { THEME_KEY } from './keys';
import { readString, writeString } from './storage';

export type Theme = 'light' | 'dark';

/** The user's explicitly-chosen theme, or null if they never picked. */
export function getStoredTheme(): Theme | null {
  const value = readString(THEME_KEY);
  return value === 'light' || value === 'dark' ? value : null;
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
  writeString(THEME_KEY, theme);
  applyTheme(theme);
}

/** Apply the effective theme. Call once before first paint. */
export function initTheme(): void {
  applyTheme(resolveTheme());
}
