import { describe, expect, it } from 'vitest';

import { formatTemporal, isForeignKeyValue, isHtmlValue, renderValue } from './format';

describe('renderValue', () => {
  it('renders null / undefined as the em-dash placeholder', () => {
    expect(renderValue(null)).toBe('—');
    expect(renderValue(undefined)).toBe('—');
  });

  it('renders booleans as Yes / No (Django admin parity)', () => {
    expect(renderValue(true)).toBe('Yes');
    expect(renderValue(false)).toBe('No');
  });

  it('passes through strings and numbers', () => {
    expect(renderValue('hello')).toBe('hello');
    expect(renderValue(0)).toBe('0');
    expect(renderValue(42)).toBe('42');
  });

  it('renders a ForeignKey envelope as its label', () => {
    expect(renderValue({ id: 7, label: 'Acme Corp' })).toBe('Acme Corp');
  });

  it('joins an array of FK envelopes by label (M2M)', () => {
    expect(
      renderValue([
        { id: 1, label: 'Alpha' },
        { id: 2, label: 'Beta' },
      ]),
    ).toBe('Alpha, Beta');
  });

  it('renders the safe-HTML envelope as stripped plain text', () => {
    expect(renderValue({ html: '<b>bold</b>' })).toBe('bold');
  });

  it('strips tags completely even on nested/overlapping input (no residual tag)', () => {
    // `<<b>script>` would survive a single naive `replace(/<[^>]*>/g,'')`
    // pass; the looped stripper must leave no angle-bracketed tag behind.
    expect(renderValue({ html: '<<b>script>alert(1)<</b>/script>' })).toBe('alert(1)');
  });
});

describe('renderValue — temporal types (#413)', () => {
  // Assertions are locale/timezone-robust: they check that the raw ISO is
  // *replaced* by a localized rendering (no `T` separator, no ISO dashes),
  // not the exact string (which varies by the runner's locale + TZ).
  it('formats a datetime away from raw ISO (localized)', () => {
    const out = renderValue('2026-05-27T12:00:00Z', 'datetime');
    expect(out).not.toBe('2026-05-27T12:00:00Z');
    expect(out).not.toContain('T'); // ISO separator gone
    expect(out).toContain('2026'); // year survives any TZ shift mid-year
  });

  it('formats a date from its Y-M-D parts (no UTC day-shift)', () => {
    const out = renderValue('2026-05-27', 'date');
    expect(out).not.toBe('2026-05-27');
    expect(out).toContain('2026');
    expect(out).toContain('27'); // day is preserved (not shifted by TZ)
  });

  it('formats a time away from raw ISO', () => {
    const out = renderValue('14:30:00', 'time');
    expect(out).not.toBe('14:30:00');
    expect(out).toContain('30'); // minutes preserved
    expect(out).toContain(':');
  });

  it('does NOT reformat a string-typed value that merely looks like a date', () => {
    // Type-keyed, not heuristic: a CharField holding an ISO-looking value
    // stays verbatim.
    expect(renderValue('2026-05-27', 'string')).toBe('2026-05-27');
  });

  it('falls back to the raw value when a temporal string is unparseable', () => {
    expect(renderValue('not-a-date', 'datetime')).toBe('not-a-date');
    expect(renderValue('nope', 'date')).toBe('nope');
  });

  it('formatTemporal returns null for non-strings, empty, and non-temporal types', () => {
    expect(formatTemporal(null, 'datetime')).toBeNull();
    expect(formatTemporal(42, 'datetime')).toBeNull();
    expect(formatTemporal('', 'date')).toBeNull();
    expect(formatTemporal('2026-05-27', 'string')).toBeNull();
  });
});

describe('isForeignKeyValue', () => {
  it('is true only for an object with both id and label', () => {
    expect(isForeignKeyValue({ id: 1, label: 'x' })).toBe(true);
    expect(isForeignKeyValue({ id: 1 })).toBe(false);
    expect(isForeignKeyValue('x')).toBe(false);
    expect(isForeignKeyValue(null)).toBe(false);
  });
});

describe('isHtmlValue', () => {
  it('is true only for an object whose html is a string', () => {
    expect(isHtmlValue({ html: '<i>x</i>' })).toBe(true);
    expect(isHtmlValue({ html: 123 })).toBe(false);
    expect(isHtmlValue('plain')).toBe(false);
    expect(isHtmlValue(null)).toBe(false);
  });
});
