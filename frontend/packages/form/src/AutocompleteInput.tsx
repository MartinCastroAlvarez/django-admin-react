// AutocompleteInput — typeahead FK picker.
//
// Used by FieldInput for foreignkey fields whose target table is too
// large to inline `choices` (the admin's autocomplete_fields case).
//
// Two modes:
//  - Display (a value is set, not editing): the related object is shown
//    as a link button to its detail page — left-click navigates, and
//    because it's a real <a href> the browser's right-click / cmd-click
//    "open in new tab" works too. A pencil switches to edit mode.
//  - Edit (no value yet, or the pencil was clicked): a debounced search
//    against the target's autocomplete endpoint. Picking a result sets
//    the value; "Cancel" reverts to the previously-selected object
//    (the value is never cleared just by entering edit mode), and
//    "Clear" empties an optional FK.
//
// The selected option's pk becomes the form value (wire §5.1).

import { useEffect, useMemo, useRef, useState } from 'react';
import { Pencil } from 'lucide-react';

import { useApiClient, useRegistry, type AutocompleteResult, type WriteValue } from '@dar/data';

interface AutocompleteInputProps {
  /** Target model the FK points at. */
  to: { app_label: string; model_name: string };
  /** Current pk value (or null). */
  value: WriteValue;
  /** Current label to display for `value` (from the read envelope). */
  initialLabel: string | undefined;
  invalid?: boolean;
  onChange: (value: WriteValue) => void;
}

export function AutocompleteInput({
  to,
  value,
  initialLabel,
  invalid,
  onChange,
}: AutocompleteInputProps) {
  const client = useApiClient();
  const registry = useRegistry();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [results, setResults] = useState<AutocompleteResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState<string | null>(initialLabel ?? null);
  const boxRef = useRef<HTMLDivElement>(null);

  const hasValue = value != null && value !== '';

  // Debounced search against the target autocomplete endpoint.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    const handle = setTimeout(() => {
      client
        .autocomplete(to.app_label, to.model_name, query)
        .then((r) => {
          if (alive) setResults(r.results);
        })
        .catch(() => {
          if (alive) setResults([]);
        })
        .finally(() => {
          if (alive) setLoading(false);
        });
    }, 250);
    return () => {
      alive = false;
      clearTimeout(handle);
    };
  }, [client, to.app_label, to.model_name, query, open]);

  // Close on outside click.
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const base = useMemo(
    () =>
      'w-full rounded border px-2 py-1 text-sm ' + (invalid ? 'border-red-400' : 'border-gray-300'),
    [invalid],
  );

  // Display mode: a value is set and we're not editing it. Render the
  // related object as a link to its detail page (right-clickable / new
  // tab) plus a pencil to switch to the search.
  if (hasValue && !editing) {
    const mount = registry.data?.mount ?? '/';
    const href = `${mount}${to.app_label}/${to.model_name}/${encodeURIComponent(String(value))}/`;
    return (
      <div className="flex items-center gap-2">
        <a
          href={href}
          className={`inline-flex items-center rounded border bg-gray-50 px-2 py-1 text-sm text-primary hover:bg-gray-100 hover:underline ${
            invalid ? 'border-red-400' : 'border-gray-300'
          }`}
        >
          {selectedLabel ?? String(value)}
        </a>
        <button
          type="button"
          aria-label="Change"
          title="Change"
          className="inline-flex shrink-0 items-center justify-center rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-800"
          onClick={() => {
            setEditing(true);
            setOpen(true);
            setQuery('');
          }}
        >
          <Pencil className="h-4 w-4" aria-hidden />
        </button>
      </div>
    );
  }

  const cancelEdit = (): void => {
    setEditing(false);
    setOpen(false);
    setQuery('');
  };

  return (
    <div ref={boxRef} className="relative">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={query}
          placeholder="Search…"
          className={base}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
        />
        {hasValue && (
          <>
            <button
              type="button"
              className="shrink-0 rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-800"
              onClick={() => {
                // Empty an optional FK; stay in edit mode so the user can
                // pick a replacement or leave it blank.
                onChange(null);
                setSelectedLabel(null);
                setQuery('');
              }}
            >
              Clear
            </button>
            <button
              type="button"
              className="shrink-0 rounded px-2 py-1 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-800"
              onClick={cancelEdit}
            >
              Cancel
            </button>
          </>
        )}
      </div>
      {open && (query.length > 0 || results.length > 0) && (
        <div className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded border border-gray-200 bg-white py-1 shadow-lg">
          {loading && <div className="px-3 py-2 text-xs text-gray-400">Searching…</div>}
          {!loading && results.length === 0 && (
            <div className="px-3 py-2 text-xs text-gray-400">No matches.</div>
          )}
          {results.map((r) => (
            <button
              key={String(r.id)}
              type="button"
              className="block w-full px-3 py-1.5 text-left text-sm hover:bg-gray-100"
              onClick={() => {
                onChange(r.id);
                setSelectedLabel(r.label);
                setOpen(false);
                setEditing(false);
                setQuery('');
              }}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
