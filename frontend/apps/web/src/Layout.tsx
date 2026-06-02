import type { PropsWithChildren } from 'react';

import { Sidebar } from '@dar/sidebar';

import { LegacyAdminBanner } from './LegacyAdminBanner';

// App shell: the navigation chrome (@dar/sidebar) plus the page content
// region, with an optional escape-hatch banner (#577) at the top of the
// content column when the consumer set
// `DJANGO_ADMIN_REACT["LEGACY_ADMIN_URL_PREFIX"]`. The banner returns
// null when the setting is unset, so it costs nothing for consumers
// who haven't enabled it.
export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      {/* Content. Extra top padding on mobile + tablet clears the fixed
          top bar (shown until lg).

          `min-w-0` is load-bearing (#672): a flex item defaults to
          `min-width: auto`, so `main` refuses to shrink below the
          intrinsic width of its widest content. A detail-page toolbar
          with 12+ action buttons makes that intrinsic width exceed the
          viewport, so `flex-1` blew `main` PAST the viewport edge and
          dragged the whole content column — title and breadcrumb
          included — off-screen, no matter how the header rows were
          stacked. `min-w-0` lets `main` shrink to the available width so
          the toolbar's `flex-wrap` can actually wrap instead of
          overflowing horizontally. */}
      <main className="min-w-0 flex-1 overflow-y-auto p-6 pt-20 lg:pt-6">
        <LegacyAdminBanner />
        {children}
      </main>
    </div>
  );
}
