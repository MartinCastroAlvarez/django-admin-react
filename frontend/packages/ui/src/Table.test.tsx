import '@testing-library/jest-dom/vitest';

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

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

  it('applies persisted column widths via a colgroup + fixed layout', () => {
    const { container } = renderTable({ columnWidths: { name: 320 } });
    expect(container.querySelector('table')?.className).toContain('table-fixed');
    const cols = container.querySelectorAll('colgroup col');
    expect(cols.length).toBeGreaterThan(0);
    // The `name` column (2nd descriptor) carries the 320px width.
    expect((cols[1] as HTMLElement).style.width).toBe('320px');
  });

  it('renders a resize handle per column when onColumnResize is set', () => {
    const { container } = renderTable({ onColumnResize: () => {} });
    expect(container.querySelectorAll('th [role="separator"]').length).toBe(columns.length);
  });

  it('reports a numeric width for the dragged column (mousedown → move)', () => {
    const onColumnResize = vi.fn();
    const { container } = renderTable({ onColumnResize, columnWidths: { name: 200 } });
    const handle = container.querySelectorAll('th [role="separator"]')[1] as HTMLElement;
    handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: 100 }));
    document.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, clientX: 160 }));
    document.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
    expect(onColumnResize).toHaveBeenCalled();
    const [key, width] = onColumnResize.mock.calls.at(-1) as [string, number];
    expect(key).toBe('name');
    expect(typeof width).toBe('number');
  });

  it('stays auto-layout with no colgroup when no widths are set', () => {
    const { container } = renderTable();
    expect(container.querySelector('table')?.className).not.toContain('table-fixed');
    expect(container.querySelector('colgroup')).toBeNull();
  });

  it('makes a sortable header keyboard-operable (tabindex + aria-sort + Enter)', () => {
    const onSort = vi.fn();
    const sortableCols: TableColumn<Row>[] = [
      { key: 'name', header: 'Name', sortable: true, render: (r) => r.name },
    ];
    const { container } = render(
      <Table columns={sortableCols} rows={rows} rowKey={(r) => r.id} onSort={onSort} />,
    );
    const th = container.querySelector('th') as HTMLElement;
    expect(th.getAttribute('tabindex')).toBe('0');
    expect(th.getAttribute('aria-sort')).toBe('none');
    fireEvent.keyDown(th, { key: 'Enter' });
    expect(onSort).toHaveBeenCalledWith('name');
    fireEvent.keyDown(th, { key: ' ' });
    expect(onSort).toHaveBeenCalledTimes(2);
  });

  it('reports the active sort direction via aria-sort', () => {
    const sortableCols: TableColumn<Row>[] = [
      { key: 'name', header: 'Name', sortable: true, render: (r) => r.name },
    ];
    const { container } = render(
      <Table
        columns={sortableCols}
        rows={rows}
        rowKey={(r) => r.id}
        onSort={() => {}}
        sortKey="name"
        sortDirection="desc"
      />,
    );
    expect((container.querySelector('th') as HTMLElement).getAttribute('aria-sort')).toBe(
      'descending',
    );
  });

  it('a non-sortable header is not focusable and has no aria-sort', () => {
    const { container } = renderTable(); // columns have no `sortable`
    const th = container.querySelector('th') as HTMLElement;
    expect(th.getAttribute('tabindex')).toBeNull();
    expect(th.getAttribute('aria-sort')).toBeNull();
  });

  describe('list_display_links (#666)', () => {
    const linkRows: Row[] = [{ id: 1, name: 'Alice' }];

    it('links the column(s) flagged isLink, not the first column, when isLink is set explicitly', () => {
      const cols: TableColumn<Row>[] = [
        { key: 'id', header: 'ID', isLink: false, render: (r) => `#${r.id}` },
        { key: 'name', header: 'Name', isLink: true, render: (r) => r.name },
      ];
      render(
        <Table columns={cols} rows={linkRows} rowKey={(r) => r.id} rowHref={(r) => `/x/${r.id}`} />,
      );
      // The `name` cell is the link; the `id` cell is plain text.
      const nameLink = screen.getByText('Alice').closest('a');
      expect(nameLink).not.toBeNull();
      expect(nameLink?.getAttribute('href')).toBe('/x/1');
      expect(screen.getByText('#1').closest('a')).toBeNull();
    });

    it('renders NO cell links and an inert row when no column is a link (list_display_links = None)', () => {
      const onRowClick = vi.fn();
      const cols: TableColumn<Row>[] = [
        { key: 'id', header: 'ID', isLink: false, render: (r) => `#${r.id}` },
        { key: 'name', header: 'Name', isLink: false, render: (r) => r.name },
      ];
      const { container } = render(
        <Table
          columns={cols}
          rows={linkRows}
          rowKey={(r) => r.id}
          rowHref={(r) => `/x/${r.id}`}
          onRowClick={onRowClick}
        />,
      );
      expect(container.querySelector('tbody a')).toBeNull();
      // Row is not clickable when nothing links.
      fireEvent.click(screen.getByText('Alice'));
      expect(onRowClick).not.toHaveBeenCalled();
      expect((container.querySelector('tbody tr') as HTMLElement).className).not.toContain(
        'cursor-pointer',
      );
    });

    it('falls back to linking the first column when no column declares isLink (legacy / pre-1.6.0)', () => {
      render(
        <Table columns={columns} rows={linkRows} rowKey={(r) => r.id} rowHref={(r) => `/x/${r.id}`} />,
      );
      // `columns` here is [id, name] with no isLink → first column links.
      expect(screen.getByText('1').closest('a')).not.toBeNull();
      expect(screen.getByText('Alice').closest('a')).toBeNull();
    });
  });
});
