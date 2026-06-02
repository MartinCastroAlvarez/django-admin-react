import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { DetailResponse, FormSpecPayload } from '@dar/data';

// Mocked SWR state the mocked useFormSpec returns, set per test.
let specState: { data: FormSpecPayload | null; loading: boolean; error: Error | null };

vi.mock('@dar/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@dar/data')>();
  return {
    ...actual,
    useApiClient: () => ({}),
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
    <ChangeForm
      data={detail()}
      appLabel="auth"
      modelName="group"
      pk="1"
      query=""
      onCancel={() => {}}
      onSave={async () => {}}
    />,
  );
}

beforeEach(() => {
  specState = { data: null, loading: false, error: null };
});

describe('ChangeForm (#659)', () => {
  it('embeds the legacy admin in an iframe when the backend returns legacy-iframe', () => {
    specState = {
      data: { renderer: 'legacy-iframe', legacy_url: '/admin/auth/group/1/change/' },
      loading: false,
      error: null,
    };
    renderChangeForm();
    const iframe = screen.getByTitle('Legacy admin form') as HTMLIFrameElement;
    expect(iframe).toBeInTheDocument();
    expect(iframe.src).toContain('/admin/auth/group/1/change/');
    // #665: the iframe is sandboxed with an explicit allowlist (no
    // allow-top-navigation / allow-popups / allow-modals).
    expect(iframe.getAttribute('sandbox')).toBe('allow-forms allow-scripts allow-same-origin');
  });

  it('rejects a javascript: legacy_url and renders an inert error card (no iframe) (#665)', () => {
    specState = {
      data: { renderer: 'legacy-iframe', legacy_url: 'javascript:fetch("/admin/")' },
      loading: false,
      error: null,
    };
    renderChangeForm();
    expect(screen.queryByTitle('Legacy admin form')).not.toBeInTheDocument();
    expect(screen.getByText(/can’t be displayed/i)).toBeInTheDocument();
  });

  it('rejects an off-origin legacy_url and renders the error card (#665)', () => {
    specState = {
      data: { renderer: 'legacy-iframe', legacy_url: 'https://attacker.example/admin/' },
      loading: false,
      error: null,
    };
    renderChangeForm();
    expect(screen.queryByTitle('Legacy admin form')).not.toBeInTheDocument();
    expect(screen.getByText(/can’t be displayed/i)).toBeInTheDocument();
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
