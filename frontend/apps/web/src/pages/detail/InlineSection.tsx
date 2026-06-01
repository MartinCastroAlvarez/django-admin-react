import { Link } from 'react-router-dom';

import { type InlineDescriptor } from '@dar/data';
import { Card, Table } from '@dar/ui';
import { FieldValueView } from '@dar/details';

import { CollapsedEmptyInline } from './CollapsedEmptyInline';

/**
 * Render one inline section in the read view (#54). Tabular inlines become
 * a table, stacked inlines a card stack; an empty addable inline collapses
 * to a single-line caret card (#591) and an empty non-addable one is hidden.
 */
export function InlineSection({ inline }: { inline: InlineDescriptor }) {
  // Empty inline (#591):
  // - Not addable → hide the whole section (Option A). Empty + read-only
  //   has zero information value and just lengthens the page.
  // - Addable → render as a single-line collapsed card with a caret
  //   (Option B). The operator can see the inline EXISTS (so they
  //   know to click Edit to add a first child) but the "No X yet"
  //   placeholder no longer eats vertical space on every load.
  if (inline.rows.length === 0) {
    if (!inline.can_add) return null;
    return <CollapsedEmptyInline label={inline.label} />;
  }

  // Per-row link to the child's own change page (#384 — Django's
  // InlineModelAdmin.show_change_link). The backend only sets the flag
  // when the child is registered, so the target always resolves.
  const changeLinkTo = (pk: string | number): string =>
    `/${inline.child.app_label}/${inline.child.model_name}/${pk}`;

  if (inline.kind === 'tabular') {
    const columns = [
      ...inline.fields.map((f) => ({
        key: f.name,
        header: f.label,
        // The pk column never truncates (#418) — a UUID/explicit pk is the
        // row's identity and link target and must stay fully readable.
        noTruncate: f.name === inline.pk_field,
        render: (row: (typeof inline.rows)[number]) => (
          <FieldValueView value={row.fields[f.name]} type={f.type} />
        ),
      })),
      ...(inline.show_change_link
        ? [
            {
              key: '__change_link',
              header: '',
              render: (row: (typeof inline.rows)[number]) => (
                <Link to={changeLinkTo(row.pk)} className="text-primary hover:underline">
                  Edit
                </Link>
              ),
            },
          ]
        : []),
    ];
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
          <div key={row.pk} className="py-3">
            <dl className="grid grid-cols-3 gap-4 text-sm">
              {inline.fields.map((f) => (
                <div key={f.name} className="contents">
                  <dt className="text-gray-500">{f.label}</dt>
                  <dd className="col-span-2 min-w-0 whitespace-pre-wrap break-words text-gray-900">
                    <FieldValueView value={row.fields[f.name]} type={f.type} />
                  </dd>
                </div>
              ))}
            </dl>
            {inline.show_change_link && (
              <div className="mt-2">
                <Link to={changeLinkTo(row.pk)} className="text-sm text-primary hover:underline">
                  Edit
                </Link>
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
