import '@testing-library/jest-dom/vitest';

import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LegacyIframe } from './LegacyIframe';

const SAME_ORIGIN = '/admin/jobs/job/1/change/?run_custom=1';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
});

describe('LegacyIframe refusal detection (#673)', () => {
  it('points the iframe src at the same URL as the Open-in-new-tab link', () => {
    render(<LegacyIframe url={SAME_ORIGIN} onCancel={() => {}} refuseAfterMs={4000} />);
    const iframe = screen.getByTitle('Legacy admin form') as HTMLIFrameElement;
    const link = screen.getByRole('link', { name: /open in new tab/i }) as HTMLAnchorElement;
    expect(iframe.src).toBe(link.href);
    expect(iframe.src).toContain('/admin/jobs/job/1/change/');
  });

  it('keeps the iframe when onLoad fires before the timeout (loaded)', () => {
    render(<LegacyIframe url={SAME_ORIGIN} onCancel={() => {}} refuseAfterMs={4000} />);
    const iframe = screen.getByTitle('Legacy admin form');
    act(() => {
      iframe.dispatchEvent(new Event('load'));
    });
    // Advancing past the refusal window must NOT flip a successfully loaded
    // frame to the fallback.
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(screen.getByTitle('Legacy admin form')).toBeInTheDocument();
    expect(screen.queryByText(/embedding refused/i)).not.toBeInTheDocument();
  });

  it('renders the refused fallback (no broken-image iframe) when onLoad never fires', () => {
    render(<LegacyIframe url={SAME_ORIGIN} onCancel={() => {}} refuseAfterMs={4000} />);
    expect(screen.getByTitle('Legacy admin form')).toBeInTheDocument();

    // No `load` event ever arrives (X-Frame-Options: DENY). After the
    // timeout the SPA concludes the frame was refused.
    act(() => {
      vi.advanceTimersByTime(4000);
    });

    // The broken-image iframe is gone; a clear fallback takes its place.
    expect(screen.queryByTitle('Legacy admin form')).not.toBeInTheDocument();
    expect(screen.getByText(/embedding refused by the legacy admin/i)).toBeInTheDocument();
    // Open-in-new-tab (the proven-working top-level navigation) is offered.
    const link = screen.getByRole('link', { name: /open in new tab/i }) as HTMLAnchorElement;
    expect(link.href).toContain('/admin/jobs/job/1/change/');
  });

  it('does not flip to refused before the timeout elapses', () => {
    render(<LegacyIframe url={SAME_ORIGIN} onCancel={() => {}} refuseAfterMs={4000} />);
    act(() => {
      vi.advanceTimersByTime(3999);
    });
    expect(screen.getByTitle('Legacy admin form')).toBeInTheDocument();
    expect(screen.queryByText(/embedding refused/i)).not.toBeInTheDocument();
  });

  it('still rejects an off-origin URL with the inert error card (no iframe, no timer)', () => {
    render(
      <LegacyIframe url="https://attacker.example/admin/" onCancel={() => {}} refuseAfterMs={4000} />,
    );
    expect(screen.queryByTitle('Legacy admin form')).not.toBeInTheDocument();
    expect(screen.getByText(/can’t be displayed/i)).toBeInTheDocument();
  });
});
