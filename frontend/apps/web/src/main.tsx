import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { ApiClient, ApiProvider, RegistryProvider } from '@dar/data';

import { App } from './App';
import './index.css';

// The mount is reconstructed from `window.location.pathname` at boot.
// Any segment up to and including `admin-react/` is the consumer-
// configured prefix. If we can't detect it, we fall back to "/".
function detectMount(): string {
  const path = window.location.pathname;
  // Look for the most common signal: a path containing "admin-react".
  // The package's RegistryView later corrects this if needed.
  const match = path.match(/^(.*?\/)/);
  return match?.[1] ?? '/';
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
