import { describe, expect, it } from 'vitest';

import {
  carryPreservedFilters,
  listPathWithPreservedFilters,
  withPreservedFilters,
} from './changelistFilters';

describe('withPreservedFilters', () => {
  it('appends the encoded list query string as _changelist_filters', () => {
    expect(withPreservedFilters('/auth/user/5', 'status=active&page=2')).toBe(
      '/auth/user/5?_changelist_filters=status%3Dactive%26page%3D2',
    );
  });

  it('tolerates a leading ?', () => {
    expect(withPreservedFilters('/a/b/1', '?q=foo')).toBe('/a/b/1?_changelist_filters=q%3Dfoo');
  });

  it('returns the bare target when there are no filters', () => {
    expect(withPreservedFilters('/a/b/1', '')).toBe('/a/b/1');
    expect(withPreservedFilters('/a/b/add', '?')).toBe('/a/b/add');
  });
});

describe('listPathWithPreservedFilters', () => {
  it('restores the list query string from _changelist_filters', () => {
    const sp = new URLSearchParams('_changelist_filters=status%3Dactive%26page%3D2&edit=1');
    expect(listPathWithPreservedFilters('/auth/user', sp)).toBe('/auth/user?status=active&page=2');
  });

  it('returns the bare list path when nothing was preserved', () => {
    expect(listPathWithPreservedFilters('/auth/user', new URLSearchParams('edit=1'))).toBe(
      '/auth/user',
    );
  });

  it('round-trips with withPreservedFilters (the full changelist state)', () => {
    const original = 'status=active&q=hi&page=3&ordering=-created';
    const detailUrl = withPreservedFilters('/a/b/9', original);
    const sp = new URLSearchParams(detailUrl.split('?')[1] ?? '');
    expect(listPathWithPreservedFilters('/a/b', sp)).toBe(`/a/b?${original}`);
  });
});

describe('carryPreservedFilters', () => {
  it('carries the param onto a target that already has a query', () => {
    const sp = new URLSearchParams('_changelist_filters=status%3Dactive');
    expect(carryPreservedFilters('/a/b/9?edit=1', sp)).toBe(
      '/a/b/9?edit=1&_changelist_filters=status%3Dactive',
    );
  });

  it('carries the param onto a target with no query', () => {
    const sp = new URLSearchParams('_changelist_filters=q%3Dx');
    expect(carryPreservedFilters('/a/b/add', sp)).toBe('/a/b/add?_changelist_filters=q%3Dx');
  });

  it('returns the target unchanged when nothing was preserved', () => {
    expect(carryPreservedFilters('/a/b/add', new URLSearchParams())).toBe('/a/b/add');
  });
});
