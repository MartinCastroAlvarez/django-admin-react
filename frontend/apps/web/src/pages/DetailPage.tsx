// DetailPage — read-only view of one object's fieldsets.
//
// Reads from `useDetail` (in @dar/data). Editing arrives in PR #7;
// this page renders the canonical detail payload as a grouped
// definition list, honouring the admin's fieldsets layout.

import { Link, useParams } from 'react-router-dom';

import { useApiClient, useDetail, type InlineDescriptor } from '@dar/data';
import { Card, EmptyState, Spinner, Table } from '@dar/ui';

import { FieldValueView } from '../components/FieldValueView';

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
                    <FieldValueView value={field.value} />
                  </dd>
                </div>
              );
            })}
          </dl>
        </Card>
      ))}

      {/* Inlines (#54): the backend surfaces ModelAdmin.inlines + their
          existing rows on the detail response. Tabular → a table,
          Stacked → a card stack. Read rendering; edit affordances are a
          follow-up gated by the per-inline can_* flags. */}
      {(data.inlines ?? [])
        .filter((inline) => inline.can_view)
        .map((inline) => (
          <InlineSection key={inline.name} inline={inline} />
        ))}
    </div>
  );
}

function InlineSection({ inline }: { inline: InlineDescriptor }) {
  if (inline.rows.length === 0) {
    return (
      <Card title={inline.label}>
        <p className="py-4 text-sm text-gray-500">No {inline.label.toLowerCase()} yet.</p>
      </Card>
    );
  }

  if (inline.kind === 'tabular') {
    const columns = inline.fields.map((f) => ({
      key: f.name,
      header: f.label,
      render: (row: (typeof inline.rows)[number]) => <FieldValueView value={row.fields[f.name]} />,
    }));
    return (
      <Card title={inline.label}>
        <Table columns={columns} rows={inline.rows} rowKey={(r) => r.pk} />
      </Card>
    );
  }

  // Stacked: one definition list per child row.
  return (
    <Card title={inline.label}>
      <div className="divide-y divide-gray-200">
        {inline.rows.map((row) => (
          <dl key={row.pk} className="grid grid-cols-3 gap-4 py-3 text-sm">
            {inline.fields.map((f) => (
              <div key={f.name} className="contents">
                <dt className="text-gray-500">{f.label}</dt>
                <dd className="col-span-2 whitespace-pre-wrap text-gray-900">
                  <FieldValueView value={row.fields[f.name]} />
                </dd>
              </div>
            ))}
          </dl>
        ))}
      </div>
    </Card>
  );
}
