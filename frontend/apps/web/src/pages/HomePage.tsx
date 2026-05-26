import { Link } from 'react-router-dom';

import { Card, EmptyState, Spinner } from '@dar/ui';
import { useRegistry } from '@dar/data';

export function HomePage() {
  const { data, loading, error } = useRegistry();

  if (loading && !data) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <Spinner label="Loading registry…" />
      </div>
    );
  }

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

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Welcome</h1>
        <p className="text-sm text-gray-500">
          Choose a model from the sidebar or click a card below.
        </p>
      </header>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.apps.flatMap((app) =>
          app.models.map((model) => (
            <Link
              key={`${app.app_label}.${model.model_name}`}
              to={`/${app.app_label}/${model.model_name}`}
              className="block hover:no-underline"
            >
              <Card title={model.verbose_name_plural || model.model_name}>
                <div className="text-xs text-gray-500">
                  {app.verbose_name} · {model.object_name}
                </div>
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
          )),
        )}
      </div>
    </div>
  );
}
