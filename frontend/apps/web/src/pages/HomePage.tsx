import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';

import { Card, EmptyState, Skeleton } from '@dar/ui';
import { useRegistry, type RegistryAppEntry, type RegistryModelEntry } from '@dar/data';
import { usePersistedSet } from '@dar/customization';

// Pinned models (#407) persist per device, like the other UI prefs.
// Keyed by the routing pair `<real_app_label>/<model_name>` so it's
// stable regardless of get_app_list grouping.
const PINNED_KEY = 'dar:pinned-models';

function routeAppFor(app: RegistryAppEntry, model: RegistryModelEntry): string {
  // Route by real_app_label (see Layout.tsx) — app.app_label may be a
  // consumer get_app_list grouping that 404s.
  return model.real_app_label || app.app_label;
}

function pinKey(app: RegistryAppEntry, model: RegistryModelEntry): string {
  return `${routeAppFor(app, model)}/${model.model_name}`;
}

export function HomePage() {
  const { data, loading, error } = useRegistry();
  const [pinned, setPinned] = usePersistedSet(PINNED_KEY);

  // Flatten registry models keyed for pinning, then pull out the pinned
  // ones (in registry order) for the top "Pinned" section.
  const pinnedModels = useMemo(() => {
    const out: Array<{ app: RegistryAppEntry; model: RegistryModelEntry; key: string }> = [];
    for (const app of data?.apps ?? []) {
      for (const model of app.models) {
        const key = pinKey(app, model);
        if (pinned.has(key)) out.push({ app, model, key });
      }
    }
    return out;
  }, [data, pinned]);

  if (loading && !data) return <HomeSkeleton />;

  if (error && !data) {
    return <EmptyState title="Couldn't load the admin" description={error.message} />;
  }

  if (!data) return null;

  if (data.apps.length === 0) {
    return (
      <EmptyState
        title="No models visible"
        description="Your account does not have permission to view any registered models."
      />
    );
  }

  const togglePin = (key: string): void =>
    setPinned((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Welcome</h1>
        <p className="text-sm text-gray-500">
          Choose a model from the sidebar or click a card below.
        </p>
      </header>

      {/* Pinned models (#407) surface at the top for quick access. */}
      {pinnedModels.length > 0 && (
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Pinned
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {pinnedModels.map(({ app, model, key }) => (
              <ModelCard
                key={key}
                app={app}
                model={model}
                pinned
                onTogglePin={() => togglePin(key)}
              />
            ))}
          </div>
        </section>
      )}

      {/* One section per app, in registry (get_app_list) order — matching
          Django admin's grouped index instead of a flat card soup. */}
      {data.apps.map((app) => (
        <section key={app.app_label}>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
            {app.verbose_name}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {app.models.map((model) => {
              const key = pinKey(app, model);
              return (
                <ModelCard
                  key={key}
                  app={app}
                  model={model}
                  pinned={pinned.has(key)}
                  onTogglePin={() => togglePin(key)}
                />
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

function ModelCard({
  app,
  model,
  pinned,
  onTogglePin,
}: {
  app: RegistryAppEntry;
  model: RegistryModelEntry;
  pinned: boolean;
  onTogglePin: () => void;
}) {
  const routeApp = routeAppFor(app, model);
  return (
    <div className="relative">
      <Link to={`/${routeApp}/${model.model_name}`} className="block hover:no-underline">
        <Card title={model.verbose_name_plural || model.model_name}>
          <div className="text-xs text-gray-500">{model.object_name}</div>
          <div className="mt-2 flex gap-2 text-xs">
            {model.permissions.view ? (
              <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700">view</span>
            ) : null}
            {model.permissions.add ? (
              <span className="px-2 py-0.5 rounded bg-green-50 text-green-700">add</span>
            ) : null}
            {model.permissions.change ? (
              <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700">change</span>
            ) : null}
            {model.permissions.delete ? (
              <span className="px-2 py-0.5 rounded bg-red-50 text-red-700">delete</span>
            ) : null}
          </div>
        </Card>
      </Link>
      {/* Star sits over the card; preventDefault stops the wrapping Link
          from navigating when toggling the pin. */}
      <button
        type="button"
        aria-label={pinned ? 'Unpin from top' : 'Pin to top'}
        aria-pressed={pinned}
        title={pinned ? 'Unpin from top' : 'Pin to top'}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onTogglePin();
        }}
        className="absolute right-2 top-2 rounded p-1 text-gray-300 hover:bg-gray-100 hover:text-amber-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <Star className={`h-4 w-4 ${pinned ? 'fill-amber-400 text-amber-400' : ''}`} aria-hidden />
      </button>
    </div>
  );
}

// First-paint skeleton for the registry index — a title block plus two
// app sections of model-card placeholders, mirroring the real grid so
// the page has weight while the registry loads (#231).
function HomeSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true">
      <span role="status" className="sr-only">
        Loading…
      </span>
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      {Array.from({ length: 2 }).map((_, s) => (
        <section key={s}>
          <Skeleton className="mb-3 h-3 w-24" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((__, c) => (
              <Card key={c}>
                <Skeleton className="h-4 w-32" />
                <Skeleton className="mt-2 h-3 w-20" />
              </Card>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
