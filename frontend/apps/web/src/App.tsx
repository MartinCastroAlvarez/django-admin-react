import { Route, Routes } from 'react-router-dom';

import { ApiError, useRegistry } from '@dar/data';

import { Layout } from './Layout';
import { HomePage } from './pages/HomePage';
import { ListPage } from './pages/ListPage';
import { DetailPage } from './pages/DetailPage';
import { LoginPage } from './pages/LoginPage';
import { CreatePage } from './pages/CreatePage';
import { ToastProvider } from './toast';

export function App() {
  const registry = useRegistry();

  // Auth gate (Issue #167). When the registry load comes back
  // unauthenticated (401) or forbidden (403), the session is invalid —
  // render the React login full-screen instead of the admin layout.
  // This only ever renders when the backend served the SPA shell to an
  // anonymous user, i.e. the consumer set
  // ``DJANGO_ADMIN_REACT["REACT_LOGIN"]``; otherwise ``SpaIndexView``
  // redirected to the HTML login and the SPA never booted. Gating on
  // the error status (not on ``data``) means a stale localStorage-cached
  // registry can't keep a dead session looking alive.
  const { error, refresh } = registry;
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
    return <LoginPage onSuccess={refresh} />;
  }

  return (
    <ToastProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path=":appLabel/:modelName" element={<ListPage />} />
          {/* Literal `add` is ranked above the `:pk` route by React
              Router, so /app/model/add opens the create form, not a
              detail with pk="add". */}
          <Route path=":appLabel/:modelName/add" element={<CreatePage />} />
          <Route path=":appLabel/:modelName/:pk" element={<DetailPage />} />
          <Route
            path="*"
            element={<div className="p-6 text-sm text-gray-500">Page not found.</div>}
          />
        </Routes>
      </Layout>
    </ToastProvider>
  );
}
