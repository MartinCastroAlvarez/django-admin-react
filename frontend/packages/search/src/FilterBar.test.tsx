import '@testing-library/jest-dom/vitest';

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import type { FilterDescriptor } from '@dar/data';

import { FilterBar } from './FilterBar';

const filters: FilterDescriptor[] = [
  {
    name: 'status',
    label: 'Status',
    type: 'choice',
    choices: [
      { value: 'a', label: 'Active' },
      { value: 'd', label: 'Done' },
    ],
  },
];

function setup(active: Record<string, string> = {}) {
  const onFilterChange = vi.fn();
  const onSearchChange = vi.fn();
  render(
    <FilterBar
      searchValue=""
      onSearchChange={onSearchChange}
      filters={filters}
      active={active}
      onFilterChange={onFilterChange}
    />,
  );
  return { onFilterChange, onSearchChange };
}

describe('FilterBar', () => {
  it('renders a dropdown button per filter and a search input', () => {
    setup();
    expect(screen.getByRole('button', { name: /Status/ })).toBeInTheDocument();
    expect(screen.getByLabelText('Search')).toBeInTheDocument();
  });

  it('opens the options popover and reports the selected value', () => {
    const { onFilterChange } = setup();
    fireEvent.click(screen.getByRole('button', { name: /Status/ }));
    fireEvent.click(screen.getByText('Active'));
    expect(onFilterChange).toHaveBeenCalledWith('status', 'a');
  });

  it('"All" clears the filter', () => {
    const { onFilterChange } = setup({ status: 'a' });
    fireEvent.click(screen.getByRole('button', { name: /Status/ }));
    fireEvent.click(screen.getByText('All'));
    expect(onFilterChange).toHaveBeenCalledWith('status', '');
  });

  it('renders trailing toolbar controls on the same row', () => {
    render(
      <FilterBar
        searchValue=""
        onSearchChange={() => {}}
        filters={filters}
        active={{ status: 'a' }}
        onFilterChange={() => {}}
        trailing={<button type="button">Customize</button>}
      />,
    );
    expect(screen.getByRole('button', { name: 'Customize' })).toBeInTheDocument();
  });

  it('relays search input changes', () => {
    const { onSearchChange } = setup();
    fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'abc' } });
    expect(onSearchChange).toHaveBeenCalledWith('abc');
  });

  it('renders `leading` content before the search input (to its left)', () => {
    render(
      <FilterBar
        searchValue=""
        onSearchChange={() => {}}
        filters={[]}
        active={{}}
        onFilterChange={() => {}}
        leading={<button type="button">Actions · 2 ▾</button>}
        trailing={<button type="button">Customize</button>}
      />,
    );
    const actions = screen.getByRole('button', { name: /Actions/ });
    const search = screen.getByLabelText('Search');
    // `leading` precedes the search input in the DOM, so the actions
    // menu sits to its left in the toolbar row.
    expect(
      actions.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
