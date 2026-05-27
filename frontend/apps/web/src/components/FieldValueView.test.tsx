import '@testing-library/jest-dom/vitest';

import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import type { FieldValue } from '@dar/data';

import { FieldValueView } from './FieldValueView';

function renderValue(value: FieldValue | undefined) {
  return render(
    <MemoryRouter>
      <FieldValueView value={value} />
    </MemoryRouter>,
  );
}

describe('FieldValueView', () => {
  it('renders a true boolean as the Yes icon (not text)', () => {
    renderValue(true);
    expect(screen.getByLabelText('Yes')).toBeInTheDocument();
  });

  it('renders a false boolean as the No icon', () => {
    renderValue(false);
    expect(screen.getByLabelText('No')).toBeInTheDocument();
  });

  it('renders the safe-HTML envelope as real markup', () => {
    // The `{ html }` envelope is the only path that emits markup; a plain
    // string never is (so untrusted CharField text stays escaped). Here we
    // assert the trusted envelope DOES render as HTML.
    const { container } = renderValue({ html: '<strong>bold</strong>' });
    const strong = container.querySelector('strong');
    expect(strong).not.toBeNull();
    expect(strong?.textContent).toBe('bold');
  });

  it('renders a registered FK as a navigable link to the related detail', () => {
    renderValue({ id: 7, label: 'Acme', to: { app_label: 'crm', model_name: 'company' } });
    const link = screen.getByRole('link', { name: 'Acme' });
    expect(link).toHaveAttribute('href', '/crm/company/7');
  });

  it('renders an unregistered FK as plain text — never a 404-bound link', () => {
    renderValue({ id: 7, label: 'Acme' });
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.getByText('Acme')).toBeInTheDocument();
  });

  it('renders a FileField value as a download link', () => {
    renderValue({ name: 'doc.pdf', url: 'https://files.example/doc.pdf', size: 1024 });
    const link = screen.getByRole('link', { name: 'doc.pdf' });
    expect(link).toHaveAttribute('href', 'https://files.example/doc.pdf');
  });

  it('renders a plain string as escaped text', () => {
    renderValue('hello world');
    expect(screen.getByText('hello world')).toBeInTheDocument();
  });

  it('renders null as the em-dash placeholder', () => {
    const { container } = renderValue(null);
    expect(container.textContent).toBe('—');
  });
});
