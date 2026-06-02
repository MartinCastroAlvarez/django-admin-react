import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import type { DetailResponse } from '@dar/data';

// Minimal read-mode detail payload — enough for the header to render with
// the title + toolbar (Refresh / Edit / Delete are permission-gated on).
function detail(
  overrides: Partial<DetailResponse> = {},
): DetailResponse {
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
    ...overrides,
  } as unknown as DetailResponse;
}

// The #672 many-actions fixture mirrored on the client: 12 batch +
// 2 detail-only object actions with long descriptions. This is what
// `examples/many_actions` (PipelineAdmin) surfaces to the SPA.
const MANY_ACTIONS = [
  'Recompute Derived Field A',
  'Recompute Derived Field B',
  'Recompute Derived Field C',
  'Re-run Pipeline Step 1',
  'Re-run Pipeline Step 2',
  'Re-run Pipeline Step 3',
  'Invalidate Downstream Cache',
  'Mark As Reviewed By Operator',
  'Mark As Pending Operator Review',
  'Export Selected Rows As CSV',
  'Export Selected Rows As JSON',
  'Notify Owner Of Selected Rows',
  'Open Detailed Audit View For This Pipeline Run',
  'Replay Last Operation On This Pipeline Run',
].map((label, i) => ({
  name: `action_${i}`,
  label,
  description: label,
  target: i < 12 ? 'batch' : 'detail',
}));

// Mutable per-test detail payload the mocked useDetail returns.
let detailState: DetailResponse = detail();

vi.mock('@dar/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@dar/data')>();
  return {
    ...actual,
    useApiClient: () => ({}),
    useDetail: () => ({ data: detailState, loading: false, error: null, refresh: async () => {} }),
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

afterEach(() => {
  detailState = detail();
});

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

  it('renders History/Refresh/Edit/Delete inline, with no ml-auto cluster (#677)', () => {
    renderPage();

    const edit = screen.getByRole('button', { name: /edit/i });
    const history = screen.getByRole('button', { name: /history/i });
    const header = edit.closest('header');
    // #677: NO `ml-auto` (or any) spacer right-aligns a subset of the
    // toolbar — two visual columns read as two toolbars. Every built-in
    // is a plain button in the single flex-wrap flow.
    expect(header?.querySelector('.ml-auto')).toBeNull();
    // History and Edit share the one flex-wrap toolbar container.
    const toolbar = history.closest('div.flex.flex-wrap');
    expect(toolbar).not.toBeNull();
    expect(edit.closest('div.flex.flex-wrap')).toBe(toolbar);
  });
});

describe('DetailPage many-actions toolbar (#672 regression guard)', () => {
  // jsdom has no layout engine, so we can't assert pixel overflow. Instead we
  // pin the CSS contract that makes wrapping (not horizontal overflow)
  // structurally inevitable when a ModelAdmin surfaces 12 batch + 2
  // detail-only actions (the examples/many_actions PipelineAdmin fixture).

  it('renders all 14 object-action buttons plus the Edit/Delete cluster', () => {
    detailState = detail({ object_actions: MANY_ACTIONS as never });
    renderPage();

    for (const action of MANY_ACTIONS) {
      expect(screen.getByRole('button', { name: action.label })).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
  });

  it('lays the toolbar out as a full-width wrapping row, separate from title/breadcrumb', () => {
    detailState = detail({ object_actions: MANY_ACTIONS as never });
    renderPage();

    const firstAction = screen.getByRole('button', { name: MANY_ACTIONS[0]!.label });
    // The toolbar row is the flex-wrap container that holds the actions.
    const toolbar = firstAction.closest('div.flex.flex-wrap');
    expect(toolbar).not.toBeNull();
    // Full width + min-w-0 so it shrinks to the viewport and `flex-wrap`
    // reflows the buttons instead of overflowing horizontally (#672).
    expect(toolbar?.className).toContain('w-full');
    expect(toolbar?.className).toContain('min-w-0');
    expect(toolbar?.className).toContain('flex-wrap');

    // The toolbar is a sibling row UNDER the H1 — it never shares the H1's
    // horizontal space (the off-screen-title regression).
    const header = toolbar?.closest('header');
    const title = screen.getByRole('heading', { level: 1 });
    expect(header).not.toBeNull();
    expect(header?.contains(title)).toBe(true);
    expect(title.contains(toolbar as Node)).toBe(false);
    expect(toolbar?.contains(title)).toBe(false);
  });

  it('renders Edit/Delete inline after the 14 actions in DOM order, no ml-auto (#677)', () => {
    detailState = detail({ object_actions: MANY_ACTIONS as never });
    renderPage();

    const edit = screen.getByRole('button', { name: /edit/i });
    const del = screen.getByRole('button', { name: /delete/i });
    const toolbar = edit.closest('div.flex.flex-wrap');
    expect(toolbar).not.toBeNull();
    // #677: no right-aligned cluster anywhere in the toolbar — Edit and
    // Delete flow inline with the custom actions in the same container.
    expect(toolbar?.querySelector('.ml-auto')).toBeNull();
    expect(del.closest('div.flex.flex-wrap')).toBe(toolbar);

    // Render order == DOM order: built-ins still come AFTER every custom
    // action (no reordering / skipping), they're just not right-aligned.
    const children = Array.from(toolbar?.children ?? []);
    const lastAction = screen.getByRole('button', {
      name: MANY_ACTIONS[MANY_ACTIONS.length - 1]!.label,
    });
    const lastActionIdx = children.findIndex((c) => c.contains(lastAction));
    const editIdx = children.findIndex((c) => c.contains(edit));
    expect(editIdx).toBeGreaterThan(lastActionIdx);
  });

  it('lets long action labels wrap inside the button (no wide min-content box)', () => {
    detailState = detail({ object_actions: MANY_ACTIONS as never });
    renderPage();

    // The longest detail-only label must not force a nowrap min-content width.
    const longest = screen.getByRole('button', {
      name: 'Open Detailed Audit View For This Pipeline Run',
    });
    expect(longest.className).toContain('whitespace-normal');
    expect(longest.className).toContain('break-words');
  });
});
