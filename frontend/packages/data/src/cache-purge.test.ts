import { beforeEach, describe, expect, it } from 'vitest';

import { purgeLocalCache } from './cache-purge';

beforeEach(() => {
  window.localStorage.clear();
});

describe('purgeLocalCache', () => {
  it('removes cached server data + per-model UI state under the dar: namespace', () => {
    window.localStorage.setItem('dar:registry:v1', JSON.stringify({ apps: [] }));
    window.localStorage.setItem('dar:list:v1', JSON.stringify({ rows: [] }));
    window.localStorage.setItem('dar:detail:v1:auth|user|7', JSON.stringify({ pk: 7 }));
    window.localStorage.setItem('dar:filters:auth:user', JSON.stringify({ q: 'x' }));
    window.localStorage.setItem('dar:cols:auth:user', JSON.stringify(['id', 'name']));

    purgeLocalCache();

    expect(window.localStorage.getItem('dar:registry:v1')).toBeNull();
    expect(window.localStorage.getItem('dar:list:v1')).toBeNull();
    expect(window.localStorage.getItem('dar:detail:v1:auth|user|7')).toBeNull();
    expect(window.localStorage.getItem('dar:filters:auth:user')).toBeNull();
    expect(window.localStorage.getItem('dar:cols:auth:user')).toBeNull();
  });

  it('preserves the dar:theme display preference across logout', () => {
    window.localStorage.setItem('dar:theme', 'dark');
    window.localStorage.setItem('dar:registry:v1', JSON.stringify({ apps: [] }));

    purgeLocalCache();

    expect(window.localStorage.getItem('dar:theme')).toBe('dark');
    expect(window.localStorage.getItem('dar:registry:v1')).toBeNull();
  });

  it('leaves non-namespaced keys untouched', () => {
    window.localStorage.setItem('unrelated', 'keep me');
    window.localStorage.setItem('dar:list:v1', JSON.stringify({ rows: [] }));

    purgeLocalCache();

    expect(window.localStorage.getItem('unrelated')).toBe('keep me');
    expect(window.localStorage.getItem('dar:list:v1')).toBeNull();
  });

  it('is a no-op when storage is empty', () => {
    expect(() => purgeLocalCache()).not.toThrow();
    expect(window.localStorage.length).toBe(0);
  });
});
