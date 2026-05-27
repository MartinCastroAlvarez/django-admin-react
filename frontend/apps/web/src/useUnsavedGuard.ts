// useUnsavedGuard (#290) — warn before losing unsaved form edits.
//
// While `dirty` is true, registers a `beforeunload` handler so closing
// the tab, reloading, or navigating to an external URL triggers the
// browser's native "Leave site? Changes may not be saved" prompt — the
// guaranteed-data-loss cases. In-app (router) navigation blocking needs
// React Router's data-router `useBlocker`, which the app's plain
// <BrowserRouter> doesn't expose yet; that's a tracked follow-up on #290.

import { useEffect } from 'react';

export function useUnsavedGuard(dirty: boolean): void {
  useEffect(() => {
    if (!dirty) return undefined;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      // Legacy browsers require returnValue to be set to show the prompt.
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);
}
