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

/**
 * Cookie the chosen theme is mirrored into so the SPA-serving view can
 * render the correct `.dark` class on `<html>` *before first paint* — no
 * light→dark flash (#84). A cookie (not just localStorage) because only the
 * server can paint pre-JS, and unlike an inline `<script>` it keeps a strict
 * `script-src 'self'` CSP intact (SECURITY.md QSEC-03). The value is a pure
 * UI pref (`light`/`dark`), never sensitive.
 */
export const THEME_COOKIE = 'dar-theme';

function writeThemeCookie(theme: Theme): void {
  if (typeof document === 'undefined') return;
  // SameSite=Lax: sent on the top-level navigation that loads the shell.
  // path=/ so it reaches the package at any mount; 1-year persistence.
  document.cookie = `${THEME_COOKIE}=${theme}; path=/; max-age=31536000; SameSite=Lax`;
}

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
  writeThemeCookie(theme);
  applyTheme(theme);
}

/** Apply the effective theme. Call once before first paint. */
export function initTheme(): void {
  applyTheme(resolveTheme());
}
