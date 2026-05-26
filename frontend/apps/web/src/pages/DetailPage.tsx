// DetailPage — read-only view of one object's fieldsets.
//
// Reads from `useDetail` (in @dar/data). Editing arrives in PR #7;
// this page renders the canonical detail payload as a grouped
// definition list, honouring the admin's fieldsets layout.

import { Link, useParams } from 'react-router-dom';

import { renderValue, useApiClient, useDetail } from '@dar/data';
import { Card, EmptyState, Spinner } from '@dar/ui';

export function DetailPage() {
  const params = useParams<{
    appLabel: string;
    modelName: string;
    pk: string;
  }>();
  const appLabel = params.appLabel ?? '';
  const modelName = params.modelName ?? '';
  const pk = params.pk ?? '';
  const client = useApiClient();
  const { data, loading, error } = useDetail({
    client,
    appLabel,
    modelName,
    pk,
  });

  if (loading && !data) return <Spinner label="Loading…" />;
  if (error && !data) {
    return <EmptyState title="Couldn't load the object" description={error.message} />;
  }
  if (!data) return null;

  return (
    <div className="space-y-4">
      <header>
        <Link to={`/${appLabel}/${modelName}`} className="text-sm text-blue-600 hover:underline">
          ← Back to list
        </Link>
        <h1 className="text-2xl font-semibold mt-1">{data.label}</h1>
        <p className="text-sm text-gray-500">
          {appLabel} · {modelName} · #{data.pk}
        </p>
      </header>

      {data.fieldsets.map((fieldset, idx) => (
        <Card key={`fs-${idx}-${fieldset.title ?? 'default'}`} title={fieldset.title ?? undefined}>
          <dl className="divide-y divide-gray-100">
            {fieldset.fields.map((name) => {
              const field = data.fields[name];
              if (!field) return null;
              return (
                <div key={name} className="py-2 grid grid-cols-3 gap-4 text-sm">
                  <dt className="text-gray-500">{field.label}</dt>
                  <dd className="col-span-2 text-gray-900 whitespace-pre-wrap">
                    {renderValue(field.value)}
                    {field.readonly && (
                      <span className="ml-2 text-xs text-gray-400">(read-only)</span>
                    )}
                  </dd>
                </div>
              );
            })}
          </dl>
        </Card>
      ))}
    </div>
  );
}
