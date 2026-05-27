import { beforeEach, describe, expect, it } from 'vitest';

import { readJSON, readString, removeKey, writeJSON, writeString } from './storage';

beforeEach(() => {
  window.localStorage.clear();
});

describe('storage', () => {
  it('round-trips strings', () => {
    writeString('dar:x', 'hello');
    expect(readString('dar:x')).toBe('hello');
  });

  it('readString returns null for a missing key', () => {
    expect(readString('dar:missing')).toBeNull();
  });

  it('round-trips JSON', () => {
    writeJSON('dar:obj', { a: 1, b: ['x'] });
    expect(readJSON('dar:obj', null)).toEqual({ a: 1, b: ['x'] });
  });

  it('readJSON returns the fallback when absent', () => {
    expect(readJSON('dar:none', { fallback: true })).toEqual({ fallback: true });
  });

  it('readJSON returns the fallback for corrupt JSON', () => {
    window.localStorage.setItem('dar:bad', 'not json{');
    expect(readJSON('dar:bad', 42)).toBe(42);
  });

  it('removeKey deletes', () => {
    writeString('dar:gone', 'v');
    removeKey('dar:gone');
    expect(readString('dar:gone')).toBeNull();
  });
});
