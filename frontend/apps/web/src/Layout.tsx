import type { PropsWithChildren } from 'react';
import { useMemo, useState } from 'react';
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

// Below this many total models the sidebar is short enough to scan by
// eye; the filter input only appears at/above it. Matches the
// `django.contrib.admin` sidebar Filter affordance (ACCEPTANCE N-9).
const FILTER_THRESHOLD = 8;

type RegistryModel = {
  model_name: string;
  verbose_name_plural?: string | null;
  real_app_label?: string | null;
};

type RegistryApp = {
  app_label: string;
  verbose_name: string;
  models: RegistryModel[];
};

// Capitalise the first letter only — matches Django admin's
// `capfirst(verbose_name_plural)`. An explicit `Meta.verbose_name_plural`
// like "Loan Package Metadata" is preserved; an auto-derived
// "loan packages" becomes "Loan packages".
function capfirst(value: string): string {
  if (!value) return value;
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function modelLabel(model: RegistryModel): string {
  return capfirst(model.verbose_name_plural || model.model_name);
}

// Keep an app when its own label matches (show all its models) or when
// at least one model label matches (show just the matching models).
// Case-insensitive substring — the same semantics as the legacy admin
// sidebar Filter. Purely client-side over the already-loaded registry;
// no API round-trip (ACCEPTANCE N-9).
function filterApps(apps: RegistryApp[], query: string): RegistryApp[] {
  const q = query.trim().toLowerCase();
  if (!q) return apps;
  const out: RegistryApp[] = [];
  for (const app of apps) {
    const appMatches =
      app.verbose_name.toLowerCase().includes(q) ||
      app.app_label.toLowerCase().includes(q);
    if (appMatches) {
      out.push(app);
      continue;
    }
    const models = app.models.filter(
      (m) =>
        modelLabel(m).toLowerCase().includes(q) ||
        m.model_name.toLowerCase().includes(q),
    );
    if (models.length > 0) out.push({ ...app, models });
  }
  return out;
}

export function Layout({ children }: PropsWithChildren) {
  const { data } = useRegistry();
  const [query, setQuery] = useState('');

  const apps = (data?.apps ?? []) as RegistryApp[];
  const totalModels = useMemo(
    () => apps.reduce((n, app) => n + app.models.length, 0),
    [apps],
  );
  const showFilter = totalModels >= FILTER_THRESHOLD;
  const visibleApps = useMemo(
    () => (showFilter ? filterApps(apps, query) : apps),
    [apps, query, showFilter],
  );

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

        {showFilter && (
          <div className="mb-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setQuery('');
              }}
              placeholder="Filter models…"
              aria-label="Filter models"
              className="w-full rounded bg-gray-800 px-2 py-1 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
            />
          </div>
        )}

        <nav className="space-y-4">
          {visibleApps.map((app) => (
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
                        {modelLabel(model)}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          {showFilter && visibleApps.length === 0 && (
            <div className="text-sm text-gray-500 px-2">
              No models match “{query}”.
            </div>
          )}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
