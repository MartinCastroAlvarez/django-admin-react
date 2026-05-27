// InlineEditor — edit an inline's child rows (Issue #54 write half UI).
//
// Renders one editable section for a single `InlineDescriptor`: each
// existing child row becomes a set of typed inputs + a "remove"
// toggle, and "Add row" appends a blank row (gated by `can_add`).
// On any change it reports the current rows as `InlineWriteItem[]`
// (the api-contract §5.2.1 shape) via `onChange`; the parent EditForm
// collects these into the PATCH body's `inlines` block.
//
// Inputs are driven by the inline field `type` (added in the read-half
// enrichment) — string/number/boolean get a matching control; FK,
// choice, date and other types fall back to a text input whose string
// value the backend formset coerces (a typed FK picker for inlines is
// a follow-up). Compile-checked; not browser-tested (no FE test runner
// yet) — flagged in the PR.

import { useEffect, useMemo, useState } from 'react';

import type { InlineDescriptor, InlineWriteItem, WriteValue } from '@dar/data';
import { Button } from '@dar/ui';

interface EditRow {
  key: string;
  pk: number | string | null;
  values: Record<string, WriteValue>;
  deleted: boolean;
}

const NUMERIC = new Set(['integer', 'float', 'decimal']);

function toInputString(value: WriteValue): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

/** Best-effort initial value for an inline cell from the read row. */
function initialCell(raw: unknown): WriteValue {
  if (raw === null || raw === undefined) return null;
  if (typeof raw === 'boolean' || typeof raw === 'number' || typeof raw === 'string') return raw;
  // FK envelope {id,label} → bare pk; anything else → empty (text).
  if (typeof raw === 'object' && !Array.isArray(raw) && 'id' in (raw as object)) {
    return (raw as { id: number | string }).id;
  }
  return null;
}

let _seq = 0;
function freshKey(): string {
  _seq += 1;
  return `new-${_seq}`;
}

export interface InlineEditorProps {
  inline: InlineDescriptor;
  /**
   * Reports the current write items (keyed by the inline `name`)
   * whenever the rows change. Pass a **stable** reference (e.g.
   * `useCallback`) — it's in this component's effect deps, so an
   * inline arrow would re-fire the effect every render.
   */
  onItems: (name: string, items: InlineWriteItem[]) => void;
}

export function InlineEditor({ inline, onItems }: InlineEditorProps) {
  const editableFields = useMemo(() => inline.fields.filter((f) => !f.readonly), [inline.fields]);

  function blankRow(): EditRow {
    return {
      key: freshKey(),
      pk: null,
      values: Object.fromEntries(editableFields.map((f) => [f.name, null as WriteValue])),
      deleted: false,
    };
  }

  const [rows, setRows] = useState<EditRow[]>(() => {
    const existing: EditRow[] = inline.rows.map((r) => ({
      key: `existing-${r.pk}`,
      pk: r.pk,
      values: Object.fromEntries(
        editableFields.map((f) => [f.name, initialCell(r.fields[f.name])]),
      ),
      deleted: false,
    }));
    // Pre-render Django's `extra` blank rows (only when the user can add),
    // capped so initial + extra never exceeds max_num. Untouched blanks
    // are dropped on save by the `touched` filter below — so they're a
    // convenience, not a forced write.
    if (!inline.can_add || inline.extra <= 0) return existing;
    const room = inline.max_num === null ? inline.extra : inline.max_num - existing.length;
    const blanks = Math.max(0, Math.min(inline.extra, room));
    return [...existing, ...Array.from({ length: blanks }, () => blankRow())];
  });

  // Report the write items to the parent whenever rows change. A row
  // with a pk + deleted → DELETE; with a pk → change; without → add.
  // New rows that the user never touched (all-empty) are dropped so an
  // accidental empty "Add row" doesn't post a blank child.
  useEffect(() => {
    const items: InlineWriteItem[] = [];
    for (const row of rows) {
      if (row.pk !== null && row.deleted) {
        items.push({ pk: row.pk, DELETE: true });
      } else if (row.pk !== null) {
        items.push({ pk: row.pk, fields: row.values });
      } else {
        const touched = Object.values(row.values).some((v) => v !== null && v !== '');
        if (touched) items.push({ pk: null, fields: row.values });
      }
    }
    onItems(inline.name, items);
  }, [rows, onItems, inline.name]);

  function setCell(rowKey: string, fieldName: string, value: WriteValue) {
    setRows((prev) =>
      prev.map((r) =>
        r.key === rowKey ? { ...r, values: { ...r.values, [fieldName]: value } } : r,
      ),
    );
  }

  function toggleDelete(rowKey: string) {
    setRows((prev) => prev.map((r) => (r.key === rowKey ? { ...r, deleted: !r.deleted } : r)));
  }

  function addRow() {
    setRows((prev) => {
      // Enforce max_num: never let the user add past the cap (Django's
      // formset would reject it on save).
      const active = prev.filter((r) => !r.deleted).length;
      if (inline.max_num !== null && active >= inline.max_num) return prev;
      return [...prev, blankRow()];
    });
  }

  function removeNewRow(rowKey: string) {
    setRows((prev) => prev.filter((r) => r.key !== rowKey));
  }

  // min_num / max_num gating (Django formset parity). `activeCount` is the
  // rows that would actually be submitted (not flagged for deletion).
  const activeCount = rows.filter((r) => !r.deleted).length;
  const minNum = inline.min_num ?? 0;
  const atMax = inline.max_num !== null && activeCount >= inline.max_num;
  const atMin = activeCount <= minNum;

  // Per-row remove affordance — shared by both layouts. An existing row
  // (has a pk) gets a "remove" checkbox (Django's DELETE), gated by
  // can_delete + min_num; a new unsaved row gets a discard ✕.
  const removeControl = (row: EditRow) =>
    row.pk !== null ? (
      inline.can_delete ? (
        <label className="flex items-center gap-1 text-xs text-gray-500">
          <input
            type="checkbox"
            checked={row.deleted}
            // Block removing below min_num: a not-yet-deleted row can't be
            // checked once at the floor (an already-checked one can still
            // be restored).
            disabled={!row.deleted && atMin}
            onChange={() => toggleDelete(row.key)}
          />
          remove
        </label>
      ) : null
    ) : (
      <button
        type="button"
        className="text-xs text-gray-400 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
        disabled={atMin}
        onClick={() => removeNewRow(row.key)}
      >
        ✕
      </button>
    );

  const addFooter = inline.can_add ? (
    <div className="flex items-center gap-3">
      <Button type="button" variant="secondary" onClick={addRow} disabled={atMax}>
        + Add {inline.label.toLowerCase()}
      </Button>
      {atMax && <span className="text-xs text-gray-500">Maximum of {inline.max_num} reached.</span>}
    </div>
  ) : null;

  // Stacked inlines (Django's StackedInline) edit as vertical label/input
  // blocks per row — never a wide table — honouring `inline.kind` (#387).
  if (inline.kind === 'stacked') {
    return (
      <div className="space-y-3">
        {rows.map((row) => (
          <div
            key={row.key}
            className={`rounded border border-gray-200 p-3 ${row.deleted ? 'opacity-40' : ''}`}
          >
            <div className="space-y-2">
              {editableFields.map((f) => (
                <div key={f.name} className="grid grid-cols-3 items-start gap-3">
                  <label className="pt-1 text-sm text-gray-500">
                    {f.label}
                    {f.required ? <span className="text-red-500"> *</span> : null}
                  </label>
                  <div className="col-span-2">
                    <InlineCellInput
                      type={f.type}
                      value={row.values[f.name] ?? null}
                      disabled={row.deleted}
                      onChange={(v) => setCell(row.key, f.name, v)}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-2 flex justify-end">{removeControl(row)}</div>
          </div>
        ))}
        {addFooter}
      </div>
    );
  }

  // Tabular inlines (the default): one row per child, columns per field.
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              {editableFields.map((f) => (
                <th key={f.name} className="py-1 pr-3 font-medium">
                  {f.label}
                  {f.required ? <span className="text-red-500"> *</span> : null}
                </th>
              ))}
              <th className="py-1" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.key}
                className={`border-b border-gray-200 ${row.deleted ? 'opacity-40' : ''}`}
              >
                {editableFields.map((f) => (
                  <td key={f.name} className="py-1 pr-3 align-top">
                    <InlineCellInput
                      type={f.type}
                      value={row.values[f.name] ?? null}
                      disabled={row.deleted}
                      onChange={(v) => setCell(row.key, f.name, v)}
                    />
                  </td>
                ))}
                <td className="py-1 align-top">{removeControl(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {addFooter}
    </div>
  );
}

interface InlineCellInputProps {
  type: string | undefined;
  value: WriteValue;
  disabled: boolean;
  onChange: (value: WriteValue) => void;
}

function InlineCellInput({ type, value, disabled, onChange }: InlineCellInputProps) {
  const cls =
    'w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1';

  if (type === 'boolean') {
    return (
      <input
        type="checkbox"
        checked={value === true}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
    );
  }
  if (type && NUMERIC.has(type)) {
    return (
      <input
        type="number"
        className={cls}
        value={toInputString(value)}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
      />
    );
  }
  // Everything else (string/text/email/url/date/datetime/fk/choice/…)
  // → text. The backend formset coerces the string to the field type.
  return (
    <input
      type="text"
      className={cls}
      value={toInputString(value)}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
    />
  );
}
