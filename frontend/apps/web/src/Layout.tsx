import type { PropsWithChildren } from 'react';

import { Sidebar } from '@dar/sidebar';

// App shell: the navigation chrome (@dar/sidebar) plus the page content
// region. Everything sidebar-shaped — brand, user actions, the Settings
// cog, the model filter, the responsive drawer — is isolated in
// @dar/sidebar so this file stays a thin two-column layout.
export function Layout({ children }: PropsWithChildren) {
  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      {/* Content. Extra top padding on mobile + tablet clears the fixed
          top bar (shown until lg). */}
      <main className="flex-1 overflow-y-auto p-6 pt-20 lg:pt-6">{children}</main>
    </div>
  );
}
