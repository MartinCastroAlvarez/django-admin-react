import '@testing-library/jest-dom/vitest';

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { RecordCardList } from './RecordCardList';
import type { TableColumn } from './Table';

interface Row {
  id: number;
  name: string;
  email: string;
}

const columns: TableColumn<Row>[] = [
  { key: 'id', header: 'ID', render: (r) => r.id },
  { key: 'name', header: 'Name', render: (r) => r.name },
  { key: 'email', header: 'Email', render: (r) => r.email },
];

const rows: Row[] = [
  { id: 1, name: 'Alice', email: 'alice@example.com' },
  { id: 2, name: 'Bob', email: 'bob@example.com' },
];

function renderList(props: Partial<React.ComponentProps<typeof RecordCardList<Row>>> = {}) {
  return render(<RecordCardList columns={columns} rows={rows} rowKey={(r) => r.id} {...props} />);
}

describe('RecordCardList', () => {
  it('renders one card per row with the non-title columns as labelled values', () => {
    renderList();
    // First column is the identity/title; the rest become label/value pairs.
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getAllByText('Email')).toHaveLength(2);
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    // The identity column does not get repeated as a label/value row.
    expect(screen.queryByText('ID')).not.toBeInTheDocument();
  });

  it('navigates on card tap via onRowClick', () => {
    const onRowClick = vi.fn();
    renderList({ onRowClick });
    // Tap a body value (the card surface) — opens the record.
    fireEvent.click(screen.getByText('Alice'));
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });

  it('renders the title (first column) as an open-in-new-tab anchor when rowHref is set', () => {
    renderList({ rowHref: (r) => `/app/model/${r.id}` });
    // The first column (`id`) is the card title and carries the anchor.
    const link = screen.getByText('1').closest('a');
    expect(link).toHaveAttribute('href', '/app/model/1');
  });

  it('does not navigate in-app on a modified (new-tab) click of the title', () => {
    const onRowClick = vi.fn();
    renderList({ onRowClick, rowHref: (r) => `/app/model/${r.id}` });
    fireEvent.click(screen.getByText('1'), { metaKey: true });
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it('toggles selection without opening the record', () => {
    const onToggleRow = vi.fn();
    const onRowClick = vi.fn();
    renderList({ selectable: true, onToggleRow, onRowClick, selectedKeys: new Set() });
    const [firstBox] = screen.getAllByRole('checkbox');
    if (!firstBox) throw new Error('expected a selection checkbox per card');
    fireEvent.click(firstBox);
    expect(onToggleRow).toHaveBeenCalledWith(1);
    // The selection click must not bubble up to the card's navigation.
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it('shows shimmer cards and marks the region busy while loading', () => {
    const { container } = renderList({ loading: true });
    expect(screen.queryByText('Alice')).not.toBeInTheDocument();
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('renders the empty label when idle and empty', () => {
    render(
      <RecordCardList columns={columns} rows={[]} rowKey={(r) => r.id} emptyLabel="Nothing here" />,
    );
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });
});
