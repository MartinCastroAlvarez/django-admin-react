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
