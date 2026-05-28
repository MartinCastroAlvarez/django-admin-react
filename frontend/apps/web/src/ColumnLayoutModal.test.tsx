// Unit tests for the contiguous-prefix lock invariant (#586). The full
// modal interactions are exercised via the page tests; this file pins
// the pure-function semantics that drive every lock / unlock click.

import { describe, expect, it } from 'vitest';

import { lockThrough, unlockFrom } from './ColumnLayoutModal';

const COLS = ['a', 'b', 'c', 'd', 'e'] as const;

describe('lockThrough', () => {
  it('locks every column from the first up to and including the target', () => {
    expect([...lockThrough(COLS, 'c')]).toEqual(['a', 'b', 'c']);
  });

  it('locking the first non-pk column just locks that one column', () => {
    expect([...lockThrough(COLS, 'a')]).toEqual(['a']);
  });

  it('locking the last column locks every non-pk column', () => {
    expect([...lockThrough(COLS, 'e')]).toEqual(['a', 'b', 'c', 'd', 'e']);
  });

  it('returns an empty set when the target name is not in the order', () => {
    expect([...lockThrough(COLS, 'missing')]).toEqual([]);
  });
});

describe('unlockFrom', () => {
  it('unlocks the target and every column to its right (contiguous-prefix rule)', () => {
    const locked = new Set(['a', 'b', 'c', 'd']);
    expect([...unlockFrom(COLS, locked, 'c')]).toEqual(['a', 'b']);
  });

  it('unlocking the first non-pk column unlocks everything', () => {
    const locked = new Set(['a', 'b', 'c', 'd', 'e']);
    expect([...unlockFrom(COLS, locked, 'a')]).toEqual([]);
  });

  it('keeps earlier locked entries unchanged when they were already locked', () => {
    const locked = new Set(['a', 'c']); // odd state, but exercises the keep-earlier rule
    expect([...unlockFrom(COLS, locked, 'c')]).toEqual(['a']);
  });

  it('returns a copy of the input when the target is not in the order', () => {
    const locked = new Set(['a', 'b']);
    const out = unlockFrom(COLS, locked, 'missing');
    expect([...out]).toEqual(['a', 'b']);
    expect(out).not.toBe(locked); // a fresh Set, not the input
  });

  it('round-trip: locking through then unlocking from yields an empty set', () => {
    const locked = lockThrough(COLS, 'd');
    expect([...unlockFrom(COLS, locked, 'a')]).toEqual([]);
  });
});
