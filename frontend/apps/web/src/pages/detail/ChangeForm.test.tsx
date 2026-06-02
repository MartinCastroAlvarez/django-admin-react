import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { DetailResponse, FormSpecPayload } from '@dar/data';

import { ToastProvider } from '../../toast';

// Mocked SWR state the mocked useFormSpec returns, set per test.
let specState: { data: FormSpecPayload | null; loading: boolean; error: Error | null };

vi.mock('@dar/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@dar/data')>();
  return {
    ...actual,
    useApiClient: () => ({ submitChangeFragment: vi.fn() }),
    useFormSpec: () => specState,
  };
});

// Import AFTER the mock so ChangeForm picks up the mocked hooks.
const { ChangeForm } = await import('./ChangeForm');

function detail(): DetailResponse {
  return {
    app_label: 'auth',
    model_name: 'group',
    pk: 1,
    label: 'editors',
    permissions: { view: true, add: true, change: true, delete: true },
    fieldsets: [{ title: null, fields: [] }],
    fields: {},
    inlines: [],
    save_options: { show_save: true },
  } as unknown as DetailResponse;
}

function renderChangeForm() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <ChangeForm
          data={detail()}
          appLabel="auth"
          modelName="group"
          pk="1"
          query=""
          onCancel={() => {}}
          onSave={async () => {}}
        />
      </ToastProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  specState = { data: null, loading: false, error: null };
});

describe('ChangeForm (#659, #679)', () => {
  it('injects the server-rendered html-fragment in-shell (no iframe) (#679)', () => {
    specState = {
      data: {
        renderer: 'html-fragment',
        html: '<form id="run-custom-form"><button type="submit">Queue</button></form>',
        csrf_token: 'tok',
        submit_url: '/admin/auth/group/1/change/',
        method: 'POST',
        messages: [],
      },
      loading: false,
      error: null,
    };
    renderChangeForm();
    // No iframe is ever rendered for a custom-template form.
    expect(document.querySelector('iframe')).toBeNull();
    // The fragment's own <form> is injected inside the SPA shell.
    expect(document.querySelector('#run-custom-form')).toBeInTheDocument();
    expect(screen.getByTestId('html-fragment-host')).toBeInTheDocument();
  });

  it('renders the form-spec fields (request-aware get_form / fieldsets) via EditForm', () => {
    specState = {
      data: {
        renderer: 'form-spec',
        fieldsets: [{ title: 'Identity', fields: ['name'], classes: ['collapse'] }],
        fields: {
          name: {
            label: 'Name',
            help_text: '',
            required: true,
            readonly: false,
            type: 'string',
            widget: { kind: 'text', attrs: { maxlength: 150 } },
            initial: 'editors',
            errors: [],
          },
        },
        variant: 'myapp.forms.GroupForm',
      },
      loading: false,
      error: null,
    };
    renderChangeForm();
    const input = screen.getByLabelText('Name', { exact: false }) as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input.value).toBe('editors');
    expect(input).toHaveAttribute('maxlength', '150');
  });

  it('falls back to a default input + note for an unregistered custom widget', () => {
    specState = {
      data: {
        renderer: 'form-spec',
        fieldsets: [{ title: null, fields: ['bio'] }],
        fields: {
          bio: {
            label: 'Bio',
            help_text: '',
            required: false,
            readonly: false,
            type: 'text',
            widget: { kind: 'custom', attrs: {}, widget_class: 'mypkg.widgets.Markdown' },
            initial: '',
            errors: [],
          },
        },
        variant: 'x',
      },
      loading: false,
      error: null,
    };
    renderChangeForm();
    expect(screen.getByText(/is not registered/i)).toBeInTheDocument();
    expect(screen.getByText('mypkg.widgets.Markdown')).toBeInTheDocument();
  });

  it('falls back to the detail-driven form when the spec errors (older backend)', () => {
    specState = { data: null, loading: false, error: new Error('404') };
    // Should not throw; renders the EditForm shell (a <form> with the Save button).
    renderChangeForm();
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
  });
});
