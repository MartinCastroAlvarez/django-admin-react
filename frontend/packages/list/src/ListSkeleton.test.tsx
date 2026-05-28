import '@testing-library/jest-dom/vitest';

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ListSkeleton } from './ListSkeleton';

describe('ListSkeleton', () => {
  it('marks the region busy and exposes a status for screen readers', () => {
    const { container } = render(<ListSkeleton />);
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
  });

  it('renders shimmer placeholders', () => {
    const { container } = render(<ListSkeleton />);
    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('honours the requested row/column counts', () => {
    const { container } = render(<ListSkeleton rows={3} columns={2} />);
    // 2 title bars + 3 toolbar bars + (3 rows × 2 cells) = 11 placeholders.
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(2 + 3 + 3 * 2);
  });
});
