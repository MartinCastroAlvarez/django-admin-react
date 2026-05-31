// Lock the prepopulated_fields behaviour (#245 / #629). Verifies:
//   1. typing in a source field slugifies the target on every keystroke
//   2. multiple sources are joined with a space, then slugified together
//   3. once the operator edits a target by hand, further changes to
//      its sources DO NOT overwrite — the manual edit wins
//   4. a target with no source values stays an empty string
import { describe, expect, it } from 'vitest';

import { applyPrepopulate } from './prepopulate';

describe('applyPrepopulate', () => {
  const prepopulated = { slug: ['title'] };

  it('slugifies the target from a single source on first edit', () => {
    const out = applyPrepopulate({
      values: { title: 'Hello World' },
      prepopulated,
      editedTargets: new Set(),
    });
    expect(out.slug).toBe('hello-world');
  });

  it('joins multiple sources with a space before slugifying', () => {
    const out = applyPrepopulate({
      values: { first: 'Acme', second: 'Holdings Inc' },
      prepopulated: { slug: ['first', 'second'] },
      editedTargets: new Set(),
    });
    expect(out.slug).toBe('acme-holdings-inc');
  });

  it('does not overwrite a target the operator has edited by hand', () => {
    const out = applyPrepopulate({
      values: { title: 'New Title', slug: 'custom-slug' },
      prepopulated,
      editedTargets: new Set(['slug']),
    });
    expect(out.slug).toBe('custom-slug');
  });

  it('leaves the target as an empty string when every source is empty', () => {
    const out = applyPrepopulate({
      values: { title: '' },
      prepopulated,
      editedTargets: new Set(),
    });
    expect(out.slug).toBe('');
  });

  it('returns a new object — does not mutate the input', () => {
    const values = { title: 'X' };
    const out = applyPrepopulate({ values, prepopulated, editedTargets: new Set() });
    expect(out).not.toBe(values);
    expect(values).not.toHaveProperty('slug');
  });
});
