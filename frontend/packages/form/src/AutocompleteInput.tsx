// AutocompleteInput — typeahead FK picker.
//
// Used by FieldInput for foreignkey fields whose target table is too
// large to inline `choices` (the admin's autocomplete_fields case).
// Debounced queries hit the target model's autocomplete endpoint; the
// selected option's pk becomes the form value (wire §5.1), the label
// is shown. Clearing the selection sets the value to null.

import { useEffect, useMemo, useRef, useState } from 'react';

import { useApiClient, type AutocompleteResult, type WriteValue } from '@dar/data';

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
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<AutocompleteResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState<string | null>(initialLabel ?? null);
  const boxRef = useRef<HTMLDivElement>(null);

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

  // Selected state: show the chosen label + a clear button.
  if (value != null && value !== '') {
    return (
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-2 rounded border border-gray-300 bg-gray-50 px-2 py-1 text-sm">
          {selectedLabel ?? String(value)}
        </span>
        <button
          type="button"
          aria-label="Change"
          title="Change"
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
          onClick={() => {
            onChange(null);
            setSelectedLabel(null);
            setQuery('');
          }}
        >
          {/* Pencil glyph (inline so @dar/form needs no icon dependency). */}
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div ref={boxRef} className="relative">
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
