import { ChevronDown } from 'lucide-react';

import { type FieldDescriptor, type FieldsetDescriptor } from '@dar/data';
import { usePersistedState } from '@dar/customization';
import { Card } from '@dar/ui';

import { DetailValue } from './DetailValue';

/**
 * Render one fieldset in the read view. Every section is collapsible
 * behind a caret (#359) and remembers its open/closed state per model +
 * section in localStorage. The default honours Django's fieldset
 * `classes` (#306): a `collapse` section starts collapsed, the rest
 * start open; any `description` shows as section help text under the
 * title. A saved preference (if present) wins over that default.
 */
export function FieldsetSection({
  fieldset,
  fields,
  persistKey,
}: {
  fieldset: FieldsetDescriptor;
  fields: Record<string, FieldDescriptor>;
  persistKey: string;
}) {
  // Default open unless Django's `collapse` class says otherwise; a saved
  // preference wins. Persistence is centralized in @dar/customization.
  const startsCollapsed = (fieldset.classes ?? []).includes('collapse');
  const [open, setOpen] = usePersistedState<boolean>(persistKey, !startsCollapsed);
  const toggle = (): void => setOpen((o) => !o);

  return (
    <Card>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-left text-base font-semibold text-gray-900"
      >
        <span>{fieldset.title ?? 'Details'}</span>
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>
      {open ? (
        <div className="mt-3">
          {fieldset.description ? (
            <p className="mb-3 text-xs text-gray-500">{fieldset.description}</p>
          ) : null}
          <dl className="divide-y divide-gray-100">
            {(fieldset.field_rows ?? fieldset.fields.map((f) => [f])).map((row, ri) => {
              // A single-field row keeps the wide label | value layout; a
              // multi-field row (Django tuple grouping, #382) lays its
              // fields side by side, each label-above-value.
              if (row.length === 1) {
                const field = fields[row[0] as string];
                if (!field) return null;
                return (
                  <div key={ri} className="grid grid-cols-3 gap-4 py-2 text-sm">
                    <dt className="text-gray-500">{field.label}</dt>
                    <dd className="col-span-2 min-w-0 whitespace-pre-wrap break-words text-gray-900">
                      <DetailValue field={field} />
                    </dd>
                  </div>
                );
              }
              return (
                <div
                  key={ri}
                  className="grid gap-4 py-2 text-sm"
                  style={{ gridTemplateColumns: `repeat(${row.length}, minmax(0, 1fr))` }}
                >
                  {row.map((name) => {
                    const field = fields[name];
                    if (!field) return null;
                    return (
                      <div key={name}>
                        <dt className="text-gray-500">{field.label}</dt>
                        <dd className="mt-0.5 min-w-0 whitespace-pre-wrap break-words text-gray-900">
                          <DetailValue field={field} />
                        </dd>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </dl>
        </div>
      ) : null}
    </Card>
  );
}
