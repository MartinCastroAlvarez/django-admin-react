import { describe, expect, it } from 'vitest';

import { isForeignKeyValue, isHtmlValue, renderValue } from './format';

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
