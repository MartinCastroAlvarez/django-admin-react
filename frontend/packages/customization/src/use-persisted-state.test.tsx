import { beforeEach, describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { usePersistedSet, usePersistedState } from './use-persisted-state';

beforeEach(() => {
  window.localStorage.clear();
});

describe('usePersistedState', () => {
  it('seeds from the default when storage is empty', () => {
    const { result } = renderHook(() => usePersistedState('dar:t', 'def'));
    expect(result.current[0]).toBe('def');
  });

  it('reads an existing value on mount', () => {
    window.localStorage.setItem('dar:t', JSON.stringify('saved'));
    const { result } = renderHook(() => usePersistedState('dar:t', 'def'));
    expect(result.current[0]).toBe('saved');
  });

  it('persists on change (value + functional updater)', () => {
    const { result } = renderHook(() => usePersistedState('dar:n', 1));
    act(() => result.current[1](2));
    expect(result.current[0]).toBe(2);
    expect(window.localStorage.getItem('dar:n')).toBe('2');
    act(() => result.current[1]((n) => n + 10));
    expect(result.current[0]).toBe(12);
    expect(window.localStorage.getItem('dar:n')).toBe('12');
  });
});

describe('usePersistedSet', () => {
  it('seeds empty, persists as an array, and re-reads', () => {
    const { result } = renderHook(() => usePersistedSet('dar:s'));
    expect(result.current[0].size).toBe(0);
    act(() => result.current[1]((prev) => new Set(prev).add('a')));
    expect(result.current[0].has('a')).toBe(true);
    expect(JSON.parse(window.localStorage.getItem('dar:s') as string)).toEqual(['a']);
  });

  it('hydrates from a stored array', () => {
    window.localStorage.setItem('dar:s', JSON.stringify(['x', 'y']));
    const { result } = renderHook(() => usePersistedSet('dar:s'));
    expect(result.current[0]).toEqual(new Set(['x', 'y']));
  });
});
