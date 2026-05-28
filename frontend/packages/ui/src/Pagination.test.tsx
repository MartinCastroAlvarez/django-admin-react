import '@testing-library/jest-dom/vitest';

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { Pagination } from './Pagination';

describe('Pagination', () => {
  it('shows the current page and total', () => {
    render(<Pagination page={2} totalPages={5} onChange={() => {}} />);
    expect(screen.getByText('Page 2 of 5')).toBeInTheDocument();
  });

  it('renders an optional count label before the page indicator', () => {
    render(<Pagination page={1} totalPages={3} countLabel="42 objects" onChange={() => {}} />);
    const nav = screen.getByRole('navigation');
    expect(nav).toHaveTextContent('42 objects');
    expect(nav).toHaveTextContent('Page 1 of 3');
  });

  it('disables Prev on the first page', () => {
    render(<Pagination page={1} totalPages={5} onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /Prev/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Next/ })).toBeEnabled();
  });

  it('disables Next on the last page', () => {
    render(<Pagination page={5} totalPages={5} onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /Next/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Prev/ })).toBeEnabled();
  });

  it('requests the neighbouring page on click', () => {
    const onChange = vi.fn();
    render(<Pagination page={3} totalPages={5} onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /Next/ }));
    expect(onChange).toHaveBeenCalledWith(4);
    fireEvent.click(screen.getByRole('button', { name: /Prev/ }));
    expect(onChange).toHaveBeenCalledWith(2);
  });

  it('does not fire onChange when the disabled edge button is clicked', () => {
    const onChange = vi.fn();
    render(<Pagination page={1} totalPages={1} onChange={onChange} />);
    fireEvent.click(screen.getByRole('button', { name: /Prev/ }));
    fireEvent.click(screen.getByRole('button', { name: /Next/ }));
    expect(onChange).not.toHaveBeenCalled();
  });
});
