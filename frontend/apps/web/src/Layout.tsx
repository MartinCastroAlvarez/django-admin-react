import type { PropsWithChildren } from 'react';
import { Link } from 'react-router-dom';

import { useRegistry } from '@dar/data';

// Brand title + logo URL are written into the SpaIndexView template
// as ``<meta name="dar-brand-title">`` / ``<meta name="dar-brand-logo">``
// so the SPA picks them up on first paint with no FOUC.
// Defaults match the legacy hardcoded shell.
function readMeta(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
  return el?.content?.trim() || null;
}

const BRAND_TITLE = readMeta('dar-brand-title') || 'django-admin-react';
const BRAND_LOGO_URL = readMeta('dar-brand-logo');

export function Layout({ children }: PropsWithChildren) {
  const { data } = useRegistry();

  return (
    <div className="flex h-full min-h-screen">
      <aside className="w-64 shrink-0 bg-gray-900 text-gray-100 p-4 overflow-y-auto">
        <div className="mb-6">
          <Link
            to="/"
            className="flex items-center gap-2 font-semibold text-lg hover:text-white"
          >
            {BRAND_LOGO_URL && (
              <img
                src={BRAND_LOGO_URL}
                alt=""
                className="h-6 w-6 rounded shrink-0"
              />
            )}
            <span>{BRAND_TITLE}</span>
          </Link>
          {data?.user && (
            <div className="text-xs text-gray-400 mt-1">
              {data.user.display_name}
              {data.user.is_superuser ? ' · superuser' : ''}
            </div>
          )}
        </div>
        <nav className="space-y-4">
          {(data?.apps ?? []).map((app) => (
            <div key={app.app_label}>
              <div className="text-xs uppercase tracking-wide text-gray-400 mb-1">
                {app.verbose_name}
              </div>
              <ul className="space-y-1">
                {app.models.map((model) => {
                  // Route by real_app_label — `app.app_label` may be a
                  // consumer `get_app_list` grouping (e.g. "financial_
                  // institutions") that does NOT round-trip through the
                  // list/detail endpoints (`resolve_model` resolves by
                  // the model's true `_meta.app_label`). Falls back to
                  // `app.app_label` for the default (ungrouped) case.
                  const routeApp = model.real_app_label || app.app_label;
                  return (
                    <li key={`${routeApp}.${model.model_name}`}>
                      <Link
                        to={`/${routeApp}/${model.model_name}`}
                        className="block text-sm px-2 py-1 rounded hover:bg-gray-800"
                      >
                        {model.verbose_name_plural || model.model_name}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
