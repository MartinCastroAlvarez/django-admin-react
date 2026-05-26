// React login page (Issue #167).
//
// Rendered full-screen by <App> when the registry load comes back
// unauthenticated (401/403) AND the consumer opted into the React
// login (the backend serves the SPA shell to anonymous users only
// when DJANGO_ADMIN_REACT["REACT_LOGIN"] is set). It POSTs to
// /api/v1/login/ via the @dar/data client — which is a thin JSON
// shell over Django's own authenticate/login (api/views/auth.py).
//
// Data-layer rule (CLAUDE.md §7): this page reaches the network only
// through @dar/data's useApiClient(); it never imports @dar/api.

import { type FormEvent, useState } from 'react';

import { ApiError, useApiClient } from '@dar/data';
import { Button, Card, Input } from '@dar/ui';

export interface LoginPageProps {
  /** Called after a successful login so the app can re-fetch state. */
  onSuccess: () => void;
  /** Optional brand title shown above the form. */
  brandTitle?: string;
}

export function LoginPage({ onSuccess, brandTitle }: LoginPageProps) {
  const client = useApiClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await client.login(username, password);
      // Success: hand back to the app to re-fetch the registry. We
      // intentionally do NOT store the returned user here — the
      // registry response is the single source of "who am I".
      onSuccess();
    } catch (err) {
      // The backend returns one generic 403 for every failure mode
      // (no username / permission enumeration), so we show one generic
      // message regardless of the cause. A non-403 (e.g. network) gets
      // its own message.
      if (err instanceof ApiError && err.status === 403) {
        setError('Invalid credentials or insufficient permissions.');
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Could not reach the server. Please try again.');
      }
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 p-2">
          <h1 className="text-center text-lg font-semibold text-gray-900">
            {brandTitle ?? 'Sign in'}
          </h1>
          <Input
            label="Username"
            name="username"
            autoComplete="username"
            autoFocus
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <Input
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={error ?? undefined}
          />
          <Button type="submit" variant="primary" loading={loading} disabled={loading}>
            Sign in
          </Button>
        </form>
      </Card>
    </div>
  );
}
