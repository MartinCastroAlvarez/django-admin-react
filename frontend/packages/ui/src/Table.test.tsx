import '@testing-library/jest-dom/vitest';

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { Table, type TableColumn } from './Table';

interface Row {
  id: number;
  name: string;
}

const columns: TableColumn<Row>[] = [
  { key: 'id', header: 'ID', render: (r) => r.id },
  { key: 'name', header: 'Name', render: (r) => r.name },
];

const rows: Row[] = [
  { id: 1, name: 'Alice' },
  { id: 2, name: 'Bob' },
];

function renderTable(props: Partial<React.ComponentProps<typeof Table<Row>>> = {}) {
  return render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} {...props} />);
}

describe('Table', () => {
  it('renders the real rows when not loading', () => {
    renderTable();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('hides the real rows and marks the region busy while loading', () => {
    const { container } = renderTable({ loading: true });
    // Cell content is replaced by skeletons — the data must not show.
    expect(screen.queryByText('Alice')).not.toBeInTheDocument();
    expect(screen.queryByText('Bob')).not.toBeInTheDocument();
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('keeps the column headers visible while loading so the layout is stable', () => {
    renderTable({ loading: true });
    expect(screen.getByText('ID')).toBeInTheDocument();
    expect(screen.getByText('Name')).toBeInTheDocument();
  });

  it('renders the requested number of skeleton rows', () => {
    const { container } = renderTable({ loading: true, skeletonRows: 5 });
    expect(container.querySelectorAll('tbody tr')).toHaveLength(5);
  });

  it('shows the empty-state when idle with no rows', () => {
    render(<Table columns={columns} rows={[]} rowKey={(r) => r.id} emptyLabel="Nothing here" />);
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('shows skeletons (not the empty-state) when loading with no rows', () => {
    const { container } = render(
      <Table columns={columns} rows={[]} rowKey={(r) => r.id} emptyLabel="Nothing here" loading />,
    );
    expect(screen.queryByText('Nothing here')).not.toBeInTheDocument();
    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });
});
