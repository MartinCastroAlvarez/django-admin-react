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
