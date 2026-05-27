import '@testing-library/jest-dom/vitest';

import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import type { FieldDescriptor } from '@dar/data';

import { FieldInput } from './FieldInput';

function pwField(overrides: Partial<FieldDescriptor> = {}): FieldDescriptor {
  return {
    type: 'string',
    label: 'API key',
    required: false,
    readonly: false,
    help_text: '',
    value: 'stored-secret',
    widget: 'password',
    ...overrides,
  };
}

describe('FieldInput password widget (#504)', () => {
  it('renders a masked input and does not seed the stored value into the DOM', () => {
    render(
      <FieldInput
        name="api_key"
        field={pwField()}
        value="stored-secret"
        error={undefined}
        onChange={() => {}}
      />,
    );
    const input = screen.getByLabelText('API key') as HTMLInputElement;
    expect(input).toHaveAttribute('type', 'password');
    // Mirrors PasswordInput(render_value=False): the stored value is never
    // placed in the DOM — the field starts empty.
    expect(input.value).toBe('');
  });

  it('reports typed characters via onChange', () => {
    const onChange = vi.fn();
    render(
      <FieldInput name="api_key" field={pwField()} value="" error={undefined} onChange={onChange} />,
    );
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'new-secret' } });
    expect(onChange).toHaveBeenCalledWith('new-secret');
  });
});
