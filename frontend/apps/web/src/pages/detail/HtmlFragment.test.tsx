// @vitest-environment-options { "runScripts": "dangerously" }
//
// The script-execution assertion needs jsdom to actually run injected
// `<script>` elements (the default jsdom config leaves them inert). Real
// browsers always run a freshly-created+inserted script — that's exactly the
// re-execution path HtmlFragment relies on for the dual-listbox JS (#679).
import '@testing-library/jest-dom/vitest';

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ChangePostPayload, HtmlFragmentResponse } from '@dar/data';

import { ToastProvider } from '../../toast';

// The SPA navigate the redirect path must call (NOT window.location).
const navigateMock = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => navigateMock };
});

// The mocked API client; `submitChangeFragment` is set per test.
const submitMock = vi.fn<(args: unknown) => Promise<ChangePostPayload>>();
vi.mock('@dar/data', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@dar/data')>();
  return { ...actual, useApiClient: () => ({ submitChangeFragment: submitMock }) };
});

const { HtmlFragment } = await import('./HtmlFragment');

function fragment(overrides: Partial<HtmlFragmentResponse> = {}): HtmlFragmentResponse {
  return {
    renderer: 'html-fragment',
    html:
      '<form id="run-custom-form">' +
      '<input type="hidden" name="selected_steps" value="fetch" />' +
      '<button type="submit">Queue</button>' +
      '</form>' +
      // Inline <script> that mutates the DOM — must execute after injection.
      // (We assert via the DOM mutation, not a window global: jsdom runs the
      // script against its own internal window, which differs from the test's
      // `window` reference, but DOM writes are observable either way — and the
      // DOM is exactly what the dual-listbox JS manipulates.)
      '<script>var f = document.getElementById("run-custom-form");' +
      'f.setAttribute("data-script-ran", String(' +
      '(parseInt(f.getAttribute("data-script-ran") || "0", 10) || 0) + 1));</script>',
    csrf_token: 'csrf-123',
    submit_url: '/admin/jobs/job/1/change/?run_custom=1',
    method: 'POST',
    messages: [],
    ...overrides,
  };
}

function renderFragment(frag: HtmlFragmentResponse) {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <HtmlFragment
          fragment={frag}
          appLabel="jobs"
          modelName="job"
          pk="1"
          query="run_custom=1"
        />
      </ToastProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  navigateMock.mockReset();
  submitMock.mockReset();
});

describe('HtmlFragment (#679)', () => {
  it('injects the fragment in-shell and EXECUTES inline <script> (no iframe)', () => {
    renderFragment(fragment());
    expect(document.querySelector('iframe')).toBeNull();
    const form = document.querySelector('#run-custom-form');
    expect(form).toBeInTheDocument();
    // The dual-listbox JS path: a naive dangerouslySetInnerHTML would NOT run
    // this; the re-execution step makes it run exactly once (the count is "1",
    // not "11" / "2" — proof it executed exactly once, not zero or twice).
    expect(form).toHaveAttribute('data-script-ran', '1');
  });

  it('round-trips a POST through a validation error (re-inject) then a redirect (navigate)', async () => {
    // First submit → another html-fragment (validation error) → re-inject;
    // second submit → redirect → SPA navigate.
    submitMock
      .mockResolvedValueOnce(
        fragment({
          html: '<form id="run-custom-form"><span class="err">Pick at least one step.</span>' +
            '<button type="submit">Queue</button></form>',
          messages: [{ level: 'error', text: 'Pick at least one step.' }],
        }),
      )
      .mockResolvedValueOnce({
        renderer: 'redirect',
        to: '/admin2/jobs/job/1/change/',
        messages: [{ level: 'success', text: 'Queued fetch' }],
      } satisfies ChangePostPayload);

    renderFragment(fragment());

    // First submit → validation re-inject, no navigation.
    fireEvent.submit(document.querySelector('#run-custom-form') as HTMLFormElement);
    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(1));
    // POSTs FormData + the fragment's CSRF token to the round-trip route.
    expect(submitMock.mock.calls[0]?.[0]).toMatchObject({
      appLabel: 'jobs',
      modelName: 'job',
      pk: '1',
      query: 'run_custom=1',
      csrfToken: 'csrf-123',
      method: 'POST',
    });
    expect(submitMock.mock.calls[0]?.[0]).toHaveProperty('body');
    // The re-injected fragment shows the validation error inside the host
    // (the same text is also toasted, so scope to the fragment host).
    const host = screen.getByTestId('html-fragment-host');
    await waitFor(() =>
      expect(within(host).getByText('Pick at least one step.')).toBeInTheDocument(),
    );
    expect(navigateMock).not.toHaveBeenCalled();

    // Second submit (on the re-injected form) → redirect → SPA navigate.
    fireEvent.submit(document.querySelector('#run-custom-form') as HTMLFormElement);
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/admin2/jobs/job/1/change/'));
  });

  it('toasts the fragment messages on initial load', () => {
    renderFragment(fragment({ messages: [{ level: 'success', text: 'Queued fetch → validate' }] }));
    expect(screen.getByText('Queued fetch → validate')).toBeInTheDocument();
  });
});
