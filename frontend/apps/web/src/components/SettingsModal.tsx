// Settings dialog (#84) — opened from the sidebar cog. v1 holds the
// appearance (light / dark) toggle; it's a natural home for future
// per-user UI preferences. Uses the shared @dar/ui Modal so it matches
// the filter / delete / action confirms (overlay, Esc / backdrop close).

import { useState } from 'react';
import { LogOut, Moon, Sun } from 'lucide-react';

import { useApiClient } from '@dar/data';
import { Button, Modal } from '@dar/ui';

import { resolveTheme, setTheme, type Theme } from '../theme';

export function SettingsModal({ onClose }: { onClose: () => void }) {
  const client = useApiClient();
  const [theme, setThemeState] = useState<Theme>(() => resolveTheme());
  const [loggingOut, setLoggingOut] = useState(false);

  const choose = (next: Theme) => {
    setTheme(next);
    setThemeState(next);
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await client.logout();
    } catch {
      // Logout is idempotent server-side; even on a transient error we
      // still bounce the user out so the UI can't pretend they're signed
      // in. The reload re-runs the auth gate (login page / Django login).
    }
    // Full reload clears all in-memory + cached state and re-enters the
    // shell, which routes an anonymous session to the login screen.
    window.location.reload();
  };

  const optionClass = (active: boolean): string =>
    [
      'flex flex-1 items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-medium',
      active
        ? 'border-blue-600 bg-blue-50 text-blue-700'
        : 'border-gray-300 text-gray-700 hover:bg-gray-50',
    ].join(' ');

  return (
    <Modal
      title="Settings"
      onClose={onClose}
      footer={
        <Button variant="primary" onClick={onClose}>
          Done
        </Button>
      }
    >
      <div className="space-y-2">
        <div className="text-sm font-medium text-gray-700">Appearance</div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => choose('light')}
            className={optionClass(theme === 'light')}
          >
            <Sun className="h-4 w-4" aria-hidden /> Light
          </button>
          <button
            type="button"
            onClick={() => choose('dark')}
            className={optionClass(theme === 'dark')}
          >
            <Moon className="h-4 w-4" aria-hidden /> Dark
          </button>
        </div>
        <p className="text-xs text-gray-500">Saved on this device.</p>
      </div>
      <div className="mt-4 space-y-2 border-t border-gray-200 pt-4">
        <div className="text-sm font-medium text-gray-700">Session</div>
        <Button variant="secondary" onClick={handleLogout} loading={loggingOut}>
          <LogOut className="h-4 w-4" aria-hidden /> Log out
        </Button>
      </div>
    </Modal>
  );
}
