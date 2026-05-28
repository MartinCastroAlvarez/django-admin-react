// AccountMenu (#578) — the panel body for the sidebar's email-with-caret
// dropdown. Replaces the old "Settings" modal: same controls (theme
// toggle + Sign out) but rendered as a dropdown panel instead of a
// modal, since the controls don't warrant a dimmed-overlay modal.
//
// This component is the panel CONTENT only — the consumer wraps it in
// the shared <Popover> so outside-click + Escape close behaviour is
// inherited from the same primitive ListPage's Actions menu uses.

import { useState } from 'react';
import { LogOut, Moon, Sun } from 'lucide-react';

import { resolveTheme, setTheme, type Theme } from '@dar/customization';
import { purgeLocalCache, useApiClient } from '@dar/data';

export interface AccountMenuProps {
  /** Hide the panel after a menu action runs (theme stays — only Sign out closes). */
  onAfterAction?: (() => void) | undefined;
  /** Email / display name shown as a small grayed caption above the controls. Optional. */
  identityLabel?: string | undefined;
  /** Role caption appended after the email (e.g. "superuser"). Optional. */
  roleLabel?: string | undefined;
}

export function AccountMenu({ onAfterAction, identityLabel, roleLabel }: AccountMenuProps) {
  const [theme, setThemeState] = useState<Theme>(() => resolveTheme());
  const client = useApiClient();
  const [loggingOut, setLoggingOut] = useState(false);

  const choose = (next: Theme) => {
    setTheme(next);
    setThemeState(next);
    // Theme is a sticky control — keep the menu open so the operator can
    // see the change reflect immediately before deciding to close it.
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await client.logout();
    } catch {
      // Logout is idempotent server-side; even on a transient network
      // error we still bounce the user out so the UI can't pretend
      // they're still signed in.
    }
    // Drop every cached server response + per-model UI hint so a logged
    // out (or next) user can't read the previous session's data out of
    // localStorage. Then a full reload re-runs the auth gate, routing an
    // anonymous session to the login screen with clean in-memory state.
    purgeLocalCache();
    onAfterAction?.();
    window.location.reload();
  };

  const optionClass = (active: boolean): string =>
    [
      'flex flex-1 items-center justify-center gap-1.5 rounded-md border px-2 py-1.5 text-sm font-medium',
      active
        ? 'border-blue-600 bg-blue-50 text-blue-700'
        : 'border-gray-300 text-gray-700 hover:bg-gray-50',
    ].join(' ');

  return (
    <div className="w-56 p-3">
      {identityLabel && (
        <div className="mb-2 truncate text-xs text-gray-500" title={identityLabel}>
          Signed in as <span className="font-medium text-gray-700">{identityLabel}</span>
          {roleLabel ? <span className="text-gray-400"> · {roleLabel}</span> : null}
        </div>
      )}

      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
        Appearance
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          role="menuitem"
          onClick={() => choose('light')}
          className={optionClass(theme === 'light')}
          aria-pressed={theme === 'light'}
        >
          <Sun className="h-4 w-4" aria-hidden /> Light
        </button>
        <button
          type="button"
          role="menuitem"
          onClick={() => choose('dark')}
          className={optionClass(theme === 'dark')}
          aria-pressed={theme === 'dark'}
        >
          <Moon className="h-4 w-4" aria-hidden /> Dark
        </button>
      </div>

      <div className="mt-3 border-t border-gray-200 pt-3">
        <button
          type="button"
          role="menuitem"
          onClick={handleLogout}
          disabled={loggingOut}
          className="flex w-full items-center justify-center gap-1.5 rounded-md border border-gray-300 px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          <LogOut className="h-4 w-4" aria-hidden />
          {loggingOut ? 'Signing out…' : 'Sign out'}
        </button>
      </div>
    </div>
  );
}
