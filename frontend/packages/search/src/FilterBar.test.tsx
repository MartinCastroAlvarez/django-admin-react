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

  it('does NOT show a typeahead box for a small filter', () => {
    setup();
    fireEvent.click(screen.getByRole('button', { name: /Status/ }));
    expect(screen.queryByPlaceholderText('Type to filter…')).not.toBeInTheDocument();
  });
});

// A filter with enough options to earn the typeahead box (>= 8).
const bigFilters: FilterDescriptor[] = [
  {
    name: 'kind',
    label: 'Kind',
    type: 'choice',
    choices: [
      { value: 'alpha', label: 'Alpha' },
      { value: 'beta', label: 'Beta' },
      { value: 'gamma', label: 'Gamma' },
      { value: 'delta', label: 'Delta' },
      { value: 'epsilon', label: 'Epsilon' },
      { value: 'zeta', label: 'Zeta' },
      { value: 'elig', label: 'Eligible' },
      { value: 'inelig', label: 'Ineligible' },
    ],
  },
];

function setupBig() {
  const onFilterChange = vi.fn();
  render(
    <FilterBar
      searchValue=""
      onSearchChange={() => {}}
      filters={bigFilters}
      active={{}}
      onFilterChange={onFilterChange}
      onClearAll={() => {}}
    />,
  );
  fireEvent.click(screen.getByRole('button', { name: /Kind/ }));
  return { onFilterChange, input: screen.getByPlaceholderText('Type to filter…') };
}

describe('FilterBar typeahead (large filter)', () => {
  it('shows the typeahead box and narrows to matching options only', () => {
    const { input } = setupBig();
    expect(input).toBeInTheDocument();
    fireEvent.change(input, { target: { value: 'elig' } });
    // Only the two matches survive; non-matches are gone.
    expect(screen.getByText('Eligible')).toBeInTheDocument();
    expect(screen.getByText('Ineligible')).toBeInTheDocument();
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument();
  });

  it('Enter selects the first match after typing', () => {
    const { onFilterChange, input } = setupBig();
    fireEvent.change(input, { target: { value: 'elig' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onFilterChange).toHaveBeenCalledWith('kind', 'elig'); // Eligible
  });

  it('Tab advances to the next valid match, then Enter selects it', () => {
    const { onFilterChange, input } = setupBig();
    fireEvent.change(input, { target: { value: 'elig' } });
    fireEvent.keyDown(input, { key: 'Tab' }); // first match → next match
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onFilterChange).toHaveBeenCalledWith('kind', 'inelig'); // Ineligible
  });

  it('shows a "No matches" hint when nothing matches', () => {
    const { input } = setupBig();
    fireEvent.change(input, { target: { value: 'zzzzz' } });
    expect(screen.getByText('No matches.')).toBeInTheDocument();
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
