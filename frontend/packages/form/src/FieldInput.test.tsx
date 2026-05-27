import '@testing-library/jest-dom/vitest';

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { FieldDescriptor } from '@dar/data';

import { FieldInput } from './FieldInput';

// A field the admin masked with PasswordInput. The backend redacts the
// stored value (#504), so the descriptor arrives with `value: null` and
// `widget: 'password'` — the SPA never receives the secret.
function pwField(overrides: Partial<FieldDescriptor> = {}): FieldDescriptor {
  return {
    type: 'string',
    label: 'API key',
    required: false,
    readonly: false,
    help_text: '',
    value: null,
    widget: 'password',
    ...overrides,
  };
}

describe('FieldInput password widget (#504)', () => {
  it('renders a masked input; the redacted value is never shown', () => {
    render(
      <FieldInput
        name="api_key"
        field={pwField()}
        value={null}
        error={undefined}
        onChange={() => {}}
      />,
    );
    const input = screen.getByLabelText('API key') as HTMLInputElement;
    expect(input).toHaveAttribute('type', 'password');
    expect(input).toHaveAttribute('autocomplete', 'new-password');
    // Backend redacted the value to null, so the field starts empty.
    expect(input.value).toBe('');
  });

  it('reports typed characters via onChange', () => {
    const onChange = vi.fn();
    render(
      <FieldInput
        name="api_key"
        field={pwField()}
        value=""
        error={undefined}
        onChange={onChange}
      />,
    );
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'new-secret' } });
    expect(onChange).toHaveBeenCalledWith('new-secret');
  });
});
