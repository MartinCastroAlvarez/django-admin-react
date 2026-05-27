import { beforeEach, describe, expect, it } from 'vitest';

import { THEME_KEY } from './keys';
import { getStoredTheme, initTheme, setTheme, THEME_COOKIE } from './theme';

beforeEach(() => {
  window.localStorage.clear();
  // Clear any dar-theme cookie left by a prior test.
  document.cookie = `${THEME_COOKIE}=; path=/; max-age=0`;
});

describe('setTheme', () => {
  it('persists the choice to localStorage', () => {
    setTheme('dark');
    expect(getStoredTheme()).toBe('dark');
    expect(window.localStorage.getItem(THEME_KEY)).toBe('dark');
  });

  it('mirrors the choice into the dar-theme cookie for server-side no-flash (#84)', () => {
    setTheme('dark');
    expect(document.cookie).toContain(`${THEME_COOKIE}=dark`);

    setTheme('light');
    expect(document.cookie).toContain(`${THEME_COOKIE}=light`);
  });
});

describe('initTheme', () => {
  it('backfills the cookie for an existing localStorage choice (#84 migration)', () => {
    // Simulate a user who picked dark before the cookie existed.
    window.localStorage.setItem(THEME_KEY, 'dark');
    expect(document.cookie).not.toContain(THEME_COOKIE);

    initTheme();

    expect(document.cookie).toContain(`${THEME_COOKIE}=dark`);
  });

  it('does not write a cookie when there is no explicit choice', () => {
    initTheme();
    expect(document.cookie).not.toContain(THEME_COOKIE);
  });
});
