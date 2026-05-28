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

function field(
  overrides: Partial<FieldDescriptor> & { type: FieldDescriptor['type'] },
): FieldDescriptor {
  return {
    label: 'F',
    required: false,
    readonly: false,
    help_text: '',
    value: null,
    ...overrides,
  } as FieldDescriptor;
}

describe('FieldInput — structured editors (#242)', () => {
  it('renders an editable monospace textarea for a json field', () => {
    const onChange = vi.fn();
    render(
      <FieldInput
        name="meta"
        field={field({ type: 'json' })}
        value={'{\n  "a": 1\n}'}
        error={undefined}
        onChange={onChange}
      />,
    );
    const box = screen.getByRole('textbox');
    expect(box.tagName).toBe('TEXTAREA');
    expect(box).toHaveValue('{\n  "a": 1\n}');
    // Edits propagate the raw string (Django parses/validates server-side).
    fireEvent.change(box, { target: { value: '{"a": 2}' } });
    expect(onChange).toHaveBeenCalledWith('{"a": 2}');
  });

  it('renders a text input for a duration field', () => {
    const onChange = vi.fn();
    render(
      <FieldInput
        name="dur"
        field={field({ type: 'duration' })}
        value="01:02:03"
        error={undefined}
        onChange={onChange}
      />,
    );
    const input = screen.getByRole('textbox');
    expect(input.tagName).toBe('INPUT');
    expect(input).toHaveValue('01:02:03');
    fireEvent.change(input, { target: { value: '1 00:00:00' } });
    expect(onChange).toHaveBeenCalledWith('1 00:00:00');
  });

  it('renders a comma-delimited text input for an array field', () => {
    const onChange = vi.fn();
    render(
      <FieldInput
        name="tags"
        field={field({ type: 'array' })}
        value="a,b,c"
        error={undefined}
        onChange={onChange}
      />,
    );
    const input = screen.getByRole('textbox');
    expect(input.tagName).toBe('INPUT');
    expect(input).toHaveValue('a,b,c');
    fireEvent.change(input, { target: { value: 'a,b' } });
    expect(onChange).toHaveBeenCalledWith('a,b');
  });

  it('keeps a readonly json field read-only (no textbox)', () => {
    render(
      <FieldInput
        name="meta"
        field={field({ type: 'json', readonly: true, value: '{"a":1}' })}
        value={null}
        error={undefined}
        onChange={() => {}}
      />,
    );
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});

describe('FieldInput — related "+add" affordance (#383)', () => {
  it('shows a "+add" button for a foreign-key field with a target model', () => {
    render(
      <FieldInput
        name="author"
        field={field({
          type: 'foreignkey',
          to: { app_label: 'lib', model_name: 'author' },
          choices: [{ value: 1, label: 'Ada' }],
        })}
        value={null}
        error={undefined}
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole('button', { name: /Add F/ })).toBeInTheDocument();
  });

  it('does NOT show "+add" for a plain choice field (no target model)', () => {
    render(
      <FieldInput
        name="status"
        field={field({ type: 'choice', choices: [{ value: 'a', label: 'Active' }] })}
        value={null}
        error={undefined}
        onChange={() => {}}
      />,
    );
    expect(screen.queryByRole('button', { name: /Add/ })).not.toBeInTheDocument();
  });

  it('does NOT show "+add" for a readonly foreign key', () => {
    render(
      <FieldInput
        name="author"
        field={field({
          type: 'foreignkey',
          readonly: true,
          to: { app_label: 'lib', model_name: 'author' },
        })}
        value={null}
        error={undefined}
        onChange={() => {}}
      />,
    );
    expect(screen.queryByRole('button', { name: /Add/ })).not.toBeInTheDocument();
  });
});
