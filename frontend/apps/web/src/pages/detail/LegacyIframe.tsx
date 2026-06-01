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

export interface LegacyIframeProps {
  url: string;
  onCancel: () => void;
}

export function LegacyIframe({ url, onCancel }: LegacyIframeProps) {
  return (
    <Card>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-gray-500">
            {t('This form is rendered by the legacy admin (custom change_form_template).')}
          </p>
          <div className="flex shrink-0 items-center gap-2">
            <a
              href={url}
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
          src={url}
          title={t('Legacy admin form')}
          className="h-[70vh] w-full rounded border border-gray-200 bg-white"
        />
      </div>
    </Card>
  );
}
