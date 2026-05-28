// Unit tests for the legacy-admin URL builder (#582). The banner
// component's render itself is exercised by the existing layout
// tests; this file pins the URL-construction contract.

import { describe, expect, it } from 'vitest';

import { legacyUrlFor } from './LegacyAdminBanner';

describe('legacyUrlFor', () => {
  it('builds a path under the legacy prefix from the SPA mount', () => {
    expect(
      legacyUrlFor('http://x/admin2/auth/user', '/admin2/', 'admin/'),
    ).toBe('/admin/auth/user/');
  });

  it('always emits a trailing slash on the path before the query string (#582)', () => {
    // Without the trailing-slash invariant, Django admin's catch_all_view
    // 404s the swapped URL. The fix ensures '/admin/<app>/<model>/'.
    expect(
      legacyUrlFor('http://x/admin2/auth/user?ordering=id', '/admin2/', 'admin/'),
    ).toBe('/admin/auth/user/?ordering=id');
  });

  it('preserves the query string verbatim (#582)', () => {
    expect(
      legacyUrlFor(
        'http://x/admin2/auth/user?status=active&page=2',
        '/admin2/',
        'admin/',
      ),
    ).toBe('/admin/auth/user/?status=active&page=2');
  });

  it('preserves a hash fragment when present (#582)', () => {
    expect(
      legacyUrlFor('http://x/admin2/auth/user#section-2', '/admin2/', 'admin/'),
    ).toBe('/admin/auth/user/#section-2');
  });

  it('handles the SPA root path → legacy root', () => {
    expect(legacyUrlFor('http://x/admin2/', '/admin2/', 'admin/')).toBe('/admin/');
  });

  it('tolerates a legacy prefix without leading or trailing slashes', () => {
    expect(legacyUrlFor('http://x/admin2/auth/user', '/admin2/', 'old-admin')).toBe(
      '/old-admin/auth/user/',
    );
  });

  it('tolerates a legacy prefix with embedded slashes', () => {
    expect(legacyUrlFor('http://x/admin2/auth/user', '/admin2/', '/admin/')).toBe(
      '/admin/auth/user/',
    );
  });

  it('falls back to the legacy root when the path is not under the SPA mount', () => {
    // Defensive: a stale `dar-mount` meta or a weird redirect lands us
    // on a path that doesn't start with the mount. Stable answer = root.
    expect(legacyUrlFor('http://x/somewhere/else', '/admin2/', 'admin/')).toBe(
      '/admin/',
    );
  });

  it('preserves a detail-page pk + query (real-world worst case)', () => {
    expect(
      legacyUrlFor(
        'http://x/admin2/auth/user/42?tab=permissions&filter=true#perms',
        '/admin2/',
        'admin/',
      ),
    ).toBe('/admin/auth/user/42/?tab=permissions&filter=true#perms');
  });
});
