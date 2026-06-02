import { Suspense, lazy } from 'react';
import { Route, Routes, useParams } from 'react-router-dom';

import { ApiError, useRegistry } from '@dar/data';
import { t } from '@dar/ui';

import { ErrorBoundary } from './ErrorBoundary';
import { Layout } from './Layout';
import { HomePage } from './pages/HomePage';
import { ListPage } from './pages/ListPage';
import { DetailPage } from './pages/DetailPage';
import { ToastProvider } from './toast';

// Route-level code-splitting (#670): the login + create pages aren't on the
// first authenticated paint — login only renders when the session is dead,
// and create only after the operator clicks "+ Add". Lazy-loading them keeps
// their code out of the main chunk. (Home / List / Detail stay eager: one of
// them is the very first paint on every load, so splitting them would only
// add a Suspense flash.)
const LoginPage = lazy(() =>
  import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })),
);
const CreatePage = lazy(() =>
  import('./pages/CreatePage').then((m) => ({ default: m.CreatePage })),
);

// Shared fallback for a lazy route chunk still in flight — a small, layout-
// neutral hint rather than a blank frame.
function RouteFallback() {
  return <div className="p-6 text-sm text-gray-500">{t('Loading…')}</div>;
}

// Remount ListPage when the model changes so per-model state (selection,
// retained "keep previous data" rows) resets cleanly on a model switch —
// while filter / page / search changes within a model keep the same
// instance so only the table skeletons, not the whole page (#368).
function KeyedListPage() {
  const { appLabel, modelName } = useParams<{ appLabel: string; modelName: string }>();
  return <ListPage key={`${appLabel}/${modelName}`} />;
}

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
    return (
      <Suspense fallback={<RouteFallback />}>
        <LoginPage onSuccess={refresh} />
      </Suspense>
    );
  }

  return (
    <ToastProvider>
      <Layout>
        {/* Catch a render throw in any page so it shows a recoverable
            fallback instead of white-screening the whole app (#415). */}
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path=":appLabel/:modelName" element={<KeyedListPage />} />
            {/* Literal `add` is ranked above the `:pk` route by React
              Router, so /app/model/add opens the create form, not a
              detail with pk="add". */}
            <Route
              path=":appLabel/:modelName/add"
              element={
                <Suspense fallback={<RouteFallback />}>
                  <CreatePage />
                </Suspense>
              }
            />
            <Route path=":appLabel/:modelName/:pk" element={<DetailPage />} />
            {/* Django-admin URL aliases (#601). When the SPA is mounted
                at the legacy admin's prefix (after a /admin/ ↔ /admin-old/
                swap), bookmarked + copy-pasted legacy URLs land here.
                Treat each as an equivalent match — same DetailPage
                component. `/change/` opens the read-only DETAILS view by
                default (#682), same as the bare `/<pk>` route; edit mode
                is one Edit-button click away, or a `?edit=1` deep link.
                Trailing slashes are normalised by React Router v6 (no
                extra route needed for "<pk>/change/" vs "<pk>/change"). */}
            <Route
              path=":appLabel/:modelName/:pk/change"
              element={<DetailPage />}
            />
            <Route
              path=":appLabel/:modelName/:pk/history"
              element={<DetailPage initialHistoryOpen />}
            />
            {/* /delete/ from the legacy admin — open the detail page and
                let the operator click the existing Delete button. No
                auto-open of the confirm modal (the SPA's Delete flow
                already fetches a cascade preview on open; an
                auto-triggered modal would surprise the user). */}
            <Route path=":appLabel/:modelName/:pk/delete" element={<DetailPage />} />
            <Route
              path="*"
              element={<div className="p-6 text-sm text-gray-500">{t('Page not found.')}</div>}
            />
          </Routes>
        </ErrorBoundary>
      </Layout>
    </ToastProvider>
  );
}
