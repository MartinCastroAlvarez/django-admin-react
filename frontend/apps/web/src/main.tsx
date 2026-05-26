import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { ApiClient, ApiProvider, RegistryProvider } from '@dar/data';

import { App } from './App';
import './index.css';

// The mount is the consumer-chosen URL prefix (e.g. `/admin-react/`,
// `/admin2/`, `/staff/`). The backend's ``SpaIndexView`` writes it to
// the ``index.html`` template as ``<meta name="dar-mount" content="...">``;
// reading that meta tag is the ground-truth signal.
//
// Issue #113: the previous implementation regexed
// ``window.location.pathname`` with ``/^(.*?\/)/`` which always
// captures just ``/`` (the first slash followed by anything). For
// ``/admin2/`` that returned ``/`` instead of ``/admin2/``, leaving
// BrowserRouter with the wrong basename so every route fell through
// to the ``*`` ("Page not found") fallback.
function detectMount(): string {
  if (typeof document !== 'undefined') {
    const meta = document.querySelector<HTMLMetaElement>('meta[name="dar-mount"]');
    if (meta?.content) {
      return meta.content;
    }
  }
  // Defensive fallback when the meta tag is missing (dev / SSR /
  // test). The previous regex was load-bearing and broken; this
  // fallback only fires when there's no meta tag at all.
  return '/';
}

const mount = detectMount();
const client = new ApiClient({ mount });

// PWA (#86): register the hand-rolled service worker the package serves
// at `<mount>sw.js`, scoped to the mount so it never claims sibling
// Django views. Best-effort — the app works fully without it, and the
// SW itself honors `Cache-Control: no-store` so authenticated reads are
// never cached. The `Service-Worker-Allowed: <mount>` header (set by
// the backend ServiceWorkerView) is what permits the mount scope.
function registerServiceWorker(mountPath: string): void {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register(`${mountPath}sw.js`, { scope: mountPath }).catch(() => {
      /* registration is best-effort; offline/install is a progressive
         enhancement, not a requirement. */
    });
  });
}
registerServiceWorker(mount);

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('#root element not found');

createRoot(rootEl).render(
  <StrictMode>
    <BrowserRouter basename={mount.replace(/\/$/, '')}>
      <ApiProvider client={client}>
        <RegistryProvider client={client}>
          <App />
        </RegistryProvider>
      </ApiProvider>
    </BrowserRouter>
  </StrictMode>,
);
