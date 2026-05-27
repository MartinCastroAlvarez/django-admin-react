// @dar/sidebar — the SPA navigation chrome: the brand header, the
// per-user actions (Settings / Install), the model filter, the
// metadata-driven app/model nav, and the responsive drawer (static
// column at ≥lg, off-canvas drawer below). The app shell composes
// <Sidebar/> next to its own <main> content region.

import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, Download, Menu, Settings } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';

import { NAV_COLLAPSE_KEY, usePersistedSet } from '@dar/customization';
import { useRegistry } from '@dar/data';
import { SettingsModal } from '@dar/settings';

// The browser's `beforeinstallprompt` event (Chromium). Captured so we
// can show an explicit "Install" affordance and call `.prompt()` on
// click — the manifest + SW (#86) make the app installable; this
// surfaces it. Typed locally since it's not in lib.dom yet.
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

function useInstallPrompt(): { canInstall: boolean; promptInstall: () => void } {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  useEffect(() => {
    function onPrompt(e: Event): void {
      e.preventDefault(); // stop Chrome's mini-infobar; we drive the UI
      setDeferred(e as BeforeInstallPromptEvent);
    }
    function onInstalled(): void {
      setDeferred(null);
    }
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);
  return {
    canInstall: deferred !== null,
    promptInstall: () => {
      if (!deferred) return;
      void deferred.prompt();
      setDeferred(null); // a prompt can only be used once
    },
  };
}

// Brand title + logo URL are written into the SpaIndexView template as
// ``<meta name="dar-brand-title">`` / ``<meta name="dar-brand-logo">``
// so the SPA picks them up on first paint with no FOUC. Defaults match
// the legacy hardcoded shell.
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
      app.verbose_name.toLowerCase().includes(q) || app.app_label.toLowerCase().includes(q);
    if (appMatches) {
      out.push(app);
      continue;
    }
    const models = app.models.filter(
      (m) => modelLabel(m).toLowerCase().includes(q) || m.model_name.toLowerCase().includes(q),
    );
    if (models.length > 0) out.push({ ...app, models });
  }
  return out;
}

export function Sidebar() {
  const { data } = useRegistry();
  const { canInstall, promptInstall } = useInstallPrompt();
  const [query, setQuery] = useState('');
  // Static column on desktop (≥ lg) and a slide-in overlay drawer below
  // so it never eats horizontal space on a phone/tablet. ``drawerOpen``
  // only affects the mobile/tablet presentation.
  const [drawerOpen, setDrawerOpen] = useState(false);
  // Settings dialog (cog) — appearance / dark-mode toggle (#84).
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Collapsed app-group sections (#227), persisted per device via
  // @dar/customization (the single home for localStorage-backed prefs).
  const [collapsed, setCollapsed] = usePersistedSet(NAV_COLLAPSE_KEY);
  const toggleApp = (appLabel: string): void => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(appLabel)) next.delete(appLabel);
      else next.add(appLabel);
      return next;
    });
  };

  // Memoised so the array identity is stable across renders — otherwise
  // the dependent `useMemo`s below recompute on every render
  // (react-hooks/exhaustive-deps).
  const apps = useMemo<RegistryApp[]>(() => (data?.apps ?? []) as RegistryApp[], [data?.apps]);
  const totalModels = useMemo(() => apps.reduce((n, app) => n + app.models.length, 0), [apps]);
  const showFilter = totalModels >= FILTER_THRESHOLD;
  const visibleApps = useMemo(
    () => (showFilter ? filterApps(apps, query) : apps),
    [apps, query, showFilter],
  );

  // Close the mobile drawer on Escape.
  useEffect(() => {
    if (!drawerOpen) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setDrawerOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  const closeDrawer = () => setDrawerOpen(false);

  return (
    <>
      {/* Top bar — hamburger + brand. Shown on mobile AND tablet; the
          static sidebar only appears at lg (≥1024px). */}
      <header className="lg:hidden fixed inset-x-0 top-0 z-30 flex h-14 items-center gap-3 bg-gray-900 px-4 text-gray-100">
        <button
          type="button"
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen(true)}
          className="-ml-2 rounded p-2 hover:bg-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
        >
          <Menu className="h-5 w-5" aria-hidden />
        </button>
        <Link to="/" onClick={closeDrawer} className="flex items-center gap-2 font-semibold">
          {BRAND_LOGO_URL && <img src={BRAND_LOGO_URL} alt="" className="h-5 w-5 rounded" />}
          <span className="truncate">{BRAND_TITLE}</span>
        </Link>
      </header>

      {/* Backdrop — on mobile + tablet while the drawer is open. */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={closeDrawer}
          aria-hidden="true"
        />
      )}

      {/* Sidebar: static column on large screens (≥lg); off-canvas
          drawer on mobile AND tablet (< lg). */}
      <aside
        className={[
          'w-64 shrink-0 overflow-y-auto bg-gray-900 p-4 text-gray-100',
          // Mobile + tablet: fixed off-canvas drawer that slides in.
          'fixed inset-y-0 left-0 z-50 transform transition-transform duration-200',
          drawerOpen ? 'translate-x-0' : '-translate-x-full',
          // Large screens (≥1024px): pinned, always visible, in normal flow.
          'lg:static lg:z-auto lg:translate-x-0',
        ].join(' ')}
      >
        <div className="mb-6">
          <Link
            to="/"
            onClick={closeDrawer}
            className="flex items-center gap-2 text-lg font-semibold hover:text-white"
          >
            {BRAND_LOGO_URL && (
              <img src={BRAND_LOGO_URL} alt="" className="h-6 w-6 shrink-0 rounded" />
            )}
            <span>{BRAND_TITLE}</span>
          </Link>
          {data?.user && (
            <div className="mt-1 text-xs text-gray-400">
              {data.user.display_name}
              {data.user.is_superuser ? ' · superuser' : ''}
            </div>
          )}
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              aria-label="Settings"
              className="inline-flex items-center gap-1.5 rounded bg-gray-800 px-2 py-1 text-xs text-gray-200 hover:bg-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
            >
              <Settings className="h-3.5 w-3.5" aria-hidden />
              Settings
            </button>
            {canInstall && (
              <button
                type="button"
                onClick={promptInstall}
                className="inline-flex items-center gap-1.5 rounded bg-gray-800 px-2 py-1 text-xs text-gray-200 hover:bg-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
              >
                <Download className="h-3.5 w-3.5" aria-hidden />
                Install app
              </button>
            )}
          </div>
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
              className="w-full rounded bg-gray-800 px-2 py-1 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus-visible:ring-1 focus-visible:ring-gray-500"
            />
          </div>
        )}

        {/* App-group sections separated by a subtle divider line, each with
            a right-aligned caret toggle — matching the Vanta sidebar's
            grouped-nav style. */}
        <nav className="divide-y divide-gray-800">
          {visibleApps.map((app) => {
            // While a filter query is active, force every group open so
            // matches are never hidden behind a collapsed section.
            const isCollapsed = !query.trim() && collapsed.has(app.app_label);
            return (
              <div key={app.app_label} className="py-3 first:pt-0">
                <button
                  type="button"
                  onClick={() => toggleApp(app.app_label)}
                  aria-expanded={!isCollapsed}
                  className="mb-1 flex w-full items-center justify-between gap-1 text-xs uppercase tracking-wide text-gray-400 hover:text-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                >
                  <span className="truncate">{app.verbose_name}</span>
                  <ChevronDown
                    className={`h-3 w-3 shrink-0 transition-transform ${
                      isCollapsed ? '-rotate-90' : ''
                    }`}
                    aria-hidden
                  />
                </button>
                {!isCollapsed && (
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
                          {/* NavLink highlights the current model — and stays
                          lit on its list, detail, edit, and add routes
                          (no `end`, so the path prefix matches). NavLink
                          sets aria-current="page" when active (#291). */}
                          <NavLink
                            to={`/${routeApp}/${model.model_name}`}
                            onClick={closeDrawer}
                            className={({ isActive }) =>
                              [
                                'block rounded px-2 py-1 text-sm',
                                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-gray-400',
                                isActive
                                  ? 'bg-gray-800 font-medium text-white'
                                  : 'hover:bg-gray-800',
                              ].join(' ')
                            }
                          >
                            {modelLabel(model)}
                          </NavLink>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
          {showFilter && visibleApps.length === 0 && (
            <div className="px-2 text-sm text-gray-500">No models match “{query}”.</div>
          )}
        </nav>
      </aside>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </>
  );
}
