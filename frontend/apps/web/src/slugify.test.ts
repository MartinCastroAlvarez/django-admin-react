import { describe, expect, it } from 'vitest';

import { slugify } from './slugify';

describe('slugify', () => {
  it('lowercases and hyphenates whitespace', () => {
    expect(slugify('Hello World')).toBe('hello-world');
  });

  it('drops punctuation and other non-word characters', () => {
    expect(slugify('Hello, World! (2026)')).toBe('hello-world-2026');
  });

  it('collapses runs of whitespace and hyphens into one hyphen', () => {
    expect(slugify('a   b---c')).toBe('a-b-c');
  });

  it('trims leading and trailing hyphens', () => {
    expect(slugify('  --Edge--  ')).toBe('edge');
  });

  it('strips accents (NFKD)', () => {
    expect(slugify('Crème Brûlée')).toBe('creme-brulee');
  });

  it('keeps digits', () => {
    expect(slugify('Q4 2026 Report')).toBe('q4-2026-report');
  });

  it('returns an empty string when nothing survives', () => {
    expect(slugify('!!!')).toBe('');
    expect(slugify('')).toBe('');
  });
});
