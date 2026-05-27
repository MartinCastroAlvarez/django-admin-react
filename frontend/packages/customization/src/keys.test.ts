import { describe, expect, it } from 'vitest';

import {
  CUSTOMIZATION_NAMESPACE,
  NAV_COLLAPSE_KEY,
  PRESERVED_ON_LOGOUT,
  THEME_KEY,
  columnsKey,
  detailCollapseKey,
  filtersKey,
} from './keys';

describe('customization keys', () => {
  it('all live under the dar: namespace', () => {
    const keys = [
      THEME_KEY,
      NAV_COLLAPSE_KEY,
      columnsKey('auth', 'user'),
      filtersKey('auth', 'user'),
      detailCollapseKey('auth', 'user', 0, 'Main'),
    ];
    for (const k of keys) expect(k.startsWith(CUSTOMIZATION_NAMESPACE)).toBe(true);
  });

  it('builds stable, model-scoped keys', () => {
    expect(columnsKey('auth', 'user')).toBe('dar:cols:auth:user');
    expect(filtersKey('auth', 'user')).toBe('dar:filters:auth:user');
    expect(detailCollapseKey('auth', 'user', 2, 'Perms')).toBe(
      'dar:detail-collapsed:auth:user:2-Perms',
    );
  });

  it('preserves only the theme across logout', () => {
    expect(PRESERVED_ON_LOGOUT).toEqual([THEME_KEY]);
  });
});
