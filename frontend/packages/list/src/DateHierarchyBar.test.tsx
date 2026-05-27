import '@testing-library/jest-dom/vitest';

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import type { DateHierarchy } from '@dar/data';

import { DateHierarchyBar } from './DateHierarchyBar';

function dh(overrides: Partial<DateHierarchy> = {}): DateHierarchy {
  return {
    field: 'created',
    granularity_options: ['year', 'month', 'day'],
    active: { year: null, month: null, day: null },
    buckets: [],
    ...overrides,
  };
}

describe('DateHierarchyBar', () => {
  it('at the year level renders year buckets and drills into the clicked year', () => {
    const onNavigate = vi.fn();
    render(
      <DateHierarchyBar
        dh={dh({
          buckets: [
            { value: 2025, count: 3 },
            { value: 2026, count: 5 },
          ],
        })}
        onNavigate={onNavigate}
      />,
    );
    // Year buckets render with their counts.
    expect(screen.getByText('2026')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();

    fireEvent.click(screen.getByText('2026'));
    expect(onNavigate).toHaveBeenCalledWith({ year: 2026 });
  });

  it('at the month level shows month-name buckets and the year breadcrumb', () => {
    const onNavigate = vi.fn();
    render(
      <DateHierarchyBar
        dh={dh({
          active: { year: 2026, month: null, day: null },
          buckets: [{ value: 1, count: 2 }],
        })}
        onNavigate={onNavigate}
      />,
    );
    // Month bucket renders as a month name, not the raw number.
    expect(screen.getByText('January')).toBeInTheDocument();

    fireEvent.click(screen.getByText('January'));
    expect(onNavigate).toHaveBeenCalledWith({ year: 2026, month: 1 });
  });

  it('breadcrumbs navigate up: "All dates" clears the drill path', () => {
    const onNavigate = vi.fn();
    render(
      <DateHierarchyBar
        dh={dh({ active: { year: 2026, month: 3, day: null }, buckets: [] })}
        onNavigate={onNavigate}
      />,
    );
    fireEvent.click(screen.getByText('All dates'));
    expect(onNavigate).toHaveBeenCalledWith({});
  });
});
