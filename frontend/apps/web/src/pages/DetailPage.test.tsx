import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import type { DetailResponse } from '@dar/data';

// Minimal read-mode detail payload — enough for the header to render with
// the title + toolbar (Refresh / Edit / Delete are permission-gated on).
function detail(): DetailResponse {
  return {
    app_label: 'auth',
    model_name: 'group',
    pk: 1,
    label: 'editors',
    permissions: { view: true, add: true, change: true, delete: true },
    fieldsets: [],
    fields: {},
    inlines: [],
    object_actions: [],
    custom_views: [],
    save_options: { show_save: true },
  } as unknown as DetailResponse;
}

vi.mock('@dar/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@dar/data')>();
  return {
    ...actual,
    useApiClient: () => ({}),
    useDetail: () => ({ data: detail(), loading: false, error: null, refresh: async () => {} }),
  };
});

vi.mock('../useModelMeta', () => ({
  useModelMeta: () => ({ plural: 'Groups' }),
}));

vi.mock('../toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
  toastMessages: vi.fn(),
}));

// Import AFTER the mocks so DetailPage picks them up.
const { DetailPage } = await import('./DetailPage');

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/auth/group/1']}>
      <Routes>
        <Route path="/:appLabel/:modelName/:pk" element={<DetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('DetailPage header (#658 regression guard)', () => {
  // The #657 module-split refactor silently reverted #658, reintroducing the
  // single-row `sm:flex-row sm:justify-between` header where a long title
  // collapsed to one-word-per-line and 8+ actions pushed the title
  // off-screen. These assertions fail the moment that layout returns.
  it('renders the title and toolbar as stacked full-width rows', () => {
    renderPage();

    const title = screen.getByRole('heading', { level: 1, name: 'editors' });
    // #658 row 2: the title wraps inside its own full-width row.
    expect(title.className).toContain('break-words');

    const header = title.closest('header');
    expect(header).not.toBeNull();
    // Stacked rows, NOT the pre-#658 side-by-side flex row.
    expect(header?.className).toContain('space-y-2');
    expect(header?.className).not.toContain('sm:flex-row');
  });

  it('floats the primary actions (Edit/Delete) to the trailing edge of their own row', () => {
    renderPage();

    const edit = screen.getByRole('button', { name: /edit/i });
    // #658 row 3: Edit/Delete live in an `ml-auto` cluster so they stay
    // trailing-edge even when the leading action cluster wraps.
    const cluster = edit.closest('div.ml-auto');
    expect(cluster).not.toBeNull();
  });
});
