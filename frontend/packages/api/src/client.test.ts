import { describe, expect, it, vi } from 'vitest';

import { ApiClient, ApiError } from './client';

// The client only reads `status`, `ok`, and `text()` off the response,
// so a minimal stub keeps the test free of any global-`Response`
// polyfill assumption.
function fakeResponse(status: number, body: unknown): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

function clientReturning(response: Response, onAuthFailure: () => void) {
  const fetchImpl = vi.fn(async () => response) as unknown as typeof fetch;
  return new ApiClient({ mount: '/admin-react/', fetchImpl, onAuthFailure });
}

describe('ApiClient — session-level auth failure (#414)', () => {
  it('invokes onAuthFailure on a 403 `session_expired` (and still throws ApiError)', async () => {
    const onAuthFailure = vi.fn();
    const client = clientReturning(
      fakeResponse(403, { error: { code: 'session_expired', message: 'Session expired.' } }),
      onAuthFailure,
    );
    await expect(client.getRegistry()).rejects.toBeInstanceOf(ApiError);
    expect(onAuthFailure).toHaveBeenCalledOnce();
  });

  it('invokes onAuthFailure on a 401', async () => {
    const onAuthFailure = vi.fn();
    const client = clientReturning(
      fakeResponse(401, { error: { code: 'not_authenticated', message: 'No session.' } }),
      onAuthFailure,
    );
    await expect(client.getRegistry()).rejects.toBeInstanceOf(ApiError);
    expect(onAuthFailure).toHaveBeenCalledOnce();
  });

  it('does NOT invoke onAuthFailure on a plain `forbidden` 403 (renders inline instead)', async () => {
    const onAuthFailure = vi.fn();
    const client = clientReturning(
      fakeResponse(403, { error: { code: 'forbidden', message: 'You do not have permission.' } }),
      onAuthFailure,
    );
    await expect(client.getRegistry()).rejects.toBeInstanceOf(ApiError);
    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it('does NOT invoke onAuthFailure on a successful response', async () => {
    const onAuthFailure = vi.fn();
    const client = clientReturning(
      fakeResponse(200, { mount: '/admin-react/', user: {}, apps: [] }),
      onAuthFailure,
    );
    await client.getRegistry();
    expect(onAuthFailure).not.toHaveBeenCalled();
  });
});

describe('ApiClient.getRecentActions (#502)', () => {
  it('GETs recent-actions/ and parses the actions array', async () => {
    const fetchImpl = vi.fn(async () =>
      fakeResponse(200, {
        actions: [
          {
            id: 1,
            action: 'changed',
            action_time: '2026-05-28T00:00:00Z',
            object_repr: 'thing',
            target: { app_label: 'auth', model_name: 'group', pk: '3' },
          },
        ],
      }),
    ) as unknown as typeof fetch;
    const client = new ApiClient({ mount: '/admin-react/', fetchImpl });

    const res = await client.getRecentActions();
    expect(res.actions).toHaveLength(1);
    expect(res.actions[0]?.target).toEqual({ app_label: 'auth', model_name: 'group', pk: '3' });

    const calls = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls;
    expect(calls[0]?.[0]).toBe('/admin-react/api/v1/recent-actions/');
  });

  it('appends the limit query param when given', async () => {
    const fetchImpl = vi.fn(
      async () => fakeResponse(200, { actions: [] }),
    ) as unknown as typeof fetch;
    const client = new ApiClient({ mount: '/admin-react/', fetchImpl });

    await client.getRecentActions(5);
    const calls = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls;
    expect(calls[0]?.[0]).toBe('/admin-react/api/v1/recent-actions/?limit=5');
  });
});
