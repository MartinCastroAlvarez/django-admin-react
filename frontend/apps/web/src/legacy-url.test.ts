import { describe, expect, it } from 'vitest';

import { safeLegacyUrl } from './legacy-url';

const ORIGIN = 'https://admin.example.com';

describe('safeLegacyUrl (#665)', () => {
  it('accepts a same-origin relative legacy-admin path and returns an absolute same-origin URL', () => {
    expect(safeLegacyUrl({ url: '/admin/auth/group/1/change/', currentOrigin: ORIGIN })).toBe(
      'https://admin.example.com/admin/auth/group/1/change/',
    );
  });

  it('accepts an absolute same-origin http(s) URL', () => {
    expect(
      safeLegacyUrl({ url: 'https://admin.example.com/admin/x/', currentOrigin: ORIGIN }),
    ).toBe('https://admin.example.com/admin/x/');
  });

  it('rejects a javascript: URL (anchor-click code execution)', () => {
    expect(safeLegacyUrl({ url: "javascript:alert(1)", currentOrigin: ORIGIN })).toBeNull();
  });

  it('rejects data: and blob: schemes', () => {
    expect(safeLegacyUrl({ url: 'data:text/html,<h1>x', currentOrigin: ORIGIN })).toBeNull();
    expect(safeLegacyUrl({ url: 'blob:https://admin.example.com/abc', currentOrigin: ORIGIN })).toBeNull();
  });

  it('rejects an off-origin http(s) URL (phishing surface inside admin chrome)', () => {
    expect(safeLegacyUrl({ url: 'https://attacker.example/', currentOrigin: ORIGIN })).toBeNull();
    expect(safeLegacyUrl({ url: '//attacker.example/x', currentOrigin: ORIGIN })).toBeNull();
  });

  it('rejects an unparseable URL', () => {
    expect(safeLegacyUrl({ url: 'http://[::bad', currentOrigin: ORIGIN })).toBeNull();
  });
});
