// LegacyIframe — embed the legacy admin change/add page inside the SPA
// shell (#659 escape hatch).
//
// When a ModelAdmin overrides `change_form_template` / `add_form_template`,
// the form can't be faithfully rendered from the JSON form spec, so the
// backend returns `{renderer: "legacy-iframe", legacy_url}`. The breadcrumb,
// sidebar, and toolbar stay SPA-rendered; only the form body is the legacy
// page. Integrators can port the custom form to documented ModelAdmin hooks
// at their own pace without blocking SPA adoption.
//
// Load-failure detection (#673): most projects mount
// `django.middleware.clickjacking.XFrameOptionsMiddleware`, which sets
// `X-Frame-Options: DENY` on EVERY response — including the legacy admin
// page. The browser then refuses to render the framed document and paints
// its broken-image glyph (document-with-X), with NO reliable `error` event
// on the `<iframe>`. We detect the refusal with a `loading | loaded |
// refused` state machine: `onLoad` flips us to `loaded`; a ~4s timeout that
// fires while still `loading` (no onLoad ever arrived) flips us to
// `refused`, and we swap the iframe for a clear fallback ("Embedding refused
// — open in new tab") instead of leaving the browser's broken-image icon on
// screen. See README › "Embedding the legacy admin" for the backend headers
// (`X-Frame-Options: SAMEORIGIN`, cross-origin `frame-ancestors`, cookies).

import { useEffect, useRef, useState } from 'react';
import { ExternalLink } from 'lucide-react';

import { Button, Card, t } from '@dar/ui';

import { safeLegacyUrl } from '../../legacy-url';

export interface LegacyIframeProps {
  url: string;
  onCancel: () => void;
  /** Milliseconds to wait for the iframe's `load` event before concluding
   *  the legacy admin refused to be framed. Exposed for tests; defaults to
   *  the 4s the issue prescribes. */
  refuseAfterMs?: number;
}

type FrameStatus = 'loading' | 'loaded' | 'refused';

export function LegacyIframe({ url, onCancel, refuseAfterMs = 4000 }: LegacyIframeProps) {
  // Validate the server-supplied `legacy_url` before it reaches the iframe
  // `src` / anchor `href` (#665): same-origin + http(s) only. A
  // `javascript:` / `data:` URL or an off-origin target is rejected and we
  // render an inert error card instead — never frame/link an unvalidated URL.
  const safe = safeLegacyUrl({ url });

  const [status, setStatus] = useState<FrameStatus>('loading');
  // Hold the timer id across renders so the cleanup can clear it.
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Arm the refusal timeout once we have a framable URL. If `onLoad` never
  // fires (X-Frame-Options: DENY / frame-ancestors block), the timeout marks
  // the frame `refused`; if it already loaded, the timeout is a no-op.
  useEffect(() => {
    if (safe === null) return;
    timerRef.current = setTimeout(() => {
      setStatus((prev) => (prev === 'loading' ? 'refused' : prev));
    }, refuseAfterMs);
    return () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
    // `safe` re-derives from `url`; re-arm if the target changes.
  }, [safe, refuseAfterMs]);

  if (safe === null) {
    return (
      <Card>
        <div className="space-y-3">
          <p className="text-sm text-red-700">
            {t('This form can’t be displayed: its address is invalid or points off-site.')}
          </p>
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t('Cancel')}
          </Button>
        </div>
      </Card>
    );
  }

  const openInNewTab = (
    <a
      href={safe}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <ExternalLink className="h-4 w-4" aria-hidden /> {t('Open in new tab')}
    </a>
  );

  // The legacy admin refused to be framed — render an explicit fallback with
  // the same Open-in-new-tab affordance, NEVER the browser's broken-image
  // glyph (#673). The "Open in new tab" link is the proven-working escape
  // hatch (a top-level navigation isn't subject to X-Frame-Options).
  if (status === 'refused') {
    return (
      <Card>
        <div className="space-y-3">
          <p className="text-sm text-gray-700">
            {t(
              'Embedding refused by the legacy admin — open in new tab. (The legacy backend' +
                ' sent X-Frame-Options / frame-ancestors that block framing; see the' +
                ' integration guide for the headers to allow it.)',
            )}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {openInNewTab}
            <Button type="button" variant="ghost" onClick={onCancel}>
              {t('Cancel')}
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-gray-500">
            {t('This form is rendered by the legacy admin (custom change_form_template).')}
          </p>
          <div className="flex shrink-0 items-center gap-2">
            {openInNewTab}
            <Button type="button" variant="ghost" onClick={onCancel}>
              {t('Cancel')}
            </Button>
          </div>
        </div>
        <iframe
          src={safe}
          title={t('Legacy admin form')}
          // Refusal detection (#673): a successful frame fires `load`; we mark
          // it `loaded` and the refusal timer becomes a no-op. (We don't try
          // to read `contentDocument` — the sandbox makes a same-origin page
          // opaque, and a thrown SecurityError would be indistinguishable from
          // success — the `load` event firing at all is the signal.)
          onLoad={() => {
            if (timerRef.current !== null) clearTimeout(timerRef.current);
            setStatus('loaded');
          }}
          // Defence-in-depth (#665): the legacy admin needs forms + scripts +
          // same-origin cookies to function, but this explicit allowlist drops
          // the unsafe-by-default capabilities — `allow-top-navigation`,
          // `allow-popups`, `allow-modals` — so a framed page can't break out
          // of the admin chrome even if `legacy_url` were ever subverted.
          sandbox="allow-forms allow-scripts allow-same-origin"
          className="h-[70vh] w-full rounded border border-gray-200 bg-white"
        />
      </div>
    </Card>
  );
}
