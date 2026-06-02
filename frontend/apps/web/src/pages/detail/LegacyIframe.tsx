// LegacyIframe — embed the legacy admin change/add page inside the SPA
// shell (#659 escape hatch).
//
// When a ModelAdmin overrides `change_form_template` / `add_form_template`,
// the form can't be faithfully rendered from the JSON form spec, so the
// backend returns `{renderer: "legacy-iframe", legacy_url}`. The breadcrumb,
// sidebar, and toolbar stay SPA-rendered; only the form body is the legacy
// page. Integrators can port the custom form to documented ModelAdmin hooks
// at their own pace without blocking SPA adoption.

import { ExternalLink } from 'lucide-react';

import { Button, Card, t } from '@dar/ui';

import { safeLegacyUrl } from '../../legacy-url';

export interface LegacyIframeProps {
  url: string;
  onCancel: () => void;
}

export function LegacyIframe({ url, onCancel }: LegacyIframeProps) {
  // Validate the server-supplied `legacy_url` before it reaches the iframe
  // `src` / anchor `href` (#665): same-origin + http(s) only. A
  // `javascript:` / `data:` URL or an off-origin target is rejected and we
  // render an inert error card instead — never frame/link an unvalidated URL.
  const safe = safeLegacyUrl({ url });

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

  return (
    <Card>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-gray-500">
            {t('This form is rendered by the legacy admin (custom change_form_template).')}
          </p>
          <div className="flex shrink-0 items-center gap-2">
            <a
              href={safe}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <ExternalLink className="h-4 w-4" aria-hidden /> {t('Open in new tab')}
            </a>
            <Button type="button" variant="ghost" onClick={onCancel}>
              {t('Cancel')}
            </Button>
          </div>
        </div>
        <iframe
          src={safe}
          title={t('Legacy admin form')}
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
