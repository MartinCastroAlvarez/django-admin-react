// ShuttleSelect — the two-pane "available / chosen" widget Django's
// HTML admin renders for ``filter_horizontal`` / ``filter_vertical``
// M2M fields (#627). Fires when the API emits ``widget: "shuttle_h"``
// or ``"shuttle_v"``; the SPA fell back to a single-list checkbox
// bank before, which doesn't scale past ~50 options.
//
// Contract:
// - ``choices`` — full set of options as ``{value, label}`` pairs.
// - ``value`` — the operator's current selection (array of choice
//   values), order-preserved.
// - ``orientation`` — ``'h'`` side-by-side (filter_horizontal), ``'v'``
//   stacked (filter_vertical).
// - ``onChange`` — fires with the new ordered array of selected values.
//
// Behaviour:
// - Each pane has its own filter input that narrows the visible items
//   client-side (no server roundtrip — the choices are already inlined).
// - Single click moves the item to the other pane (matches Django).
// - "Choose all" / "Remove all" links act on the FILTERED view, so
//   typing a search term + clicking the link affects only those items.
// - Selection order is preserved: when an item is moved INTO chosen, it
//   appends; when moved out, the relative order of remaining items is
//   kept. Matches Django's admin.

import { useId, useMemo, useState } from 'react';

import type { FieldChoice, WriteValue } from '@dar/data';

interface ShuttleSelectProps {
  /** Stable id prefix for the search inputs (a11y labelling). */
  id: string;
  /** Inlined choice list — the same shape as ``field.choices``. */
  choices: FieldChoice[];
  /** Currently selected values (array of choice values). */
  value: WriteValue;
  /** ``filter_horizontal`` → ``'h'``; ``filter_vertical`` → ``'v'``. */
  orientation: 'h' | 'v';
  /** Label of the field (drives the "Available <label>" header text). */
  label: string;
  onChange: (next: Array<string | number>) => void;
}

function asArray(v: WriteValue): Array<string | number> {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string | number => typeof x === 'string' || typeof x === 'number');
}

/** Narrow a FieldChoice's `value` to the string|number M2M-pk shape.
 *  `FieldChoice.value` is widened to ``boolean | null`` to cover
 *  choice fields; M2M pks can only be string/number, so we narrow
 *  before any compare / emit. Returns `null` for the (unexpected)
 *  bool/null cases; callers filter those out. */
function pkOf(c: FieldChoice): string | number | null {
  return typeof c.value === 'string' || typeof c.value === 'number' ? c.value : null;
}

function matchesFilter(label: string, q: string): boolean {
  if (!q) return true;
  return label.toLowerCase().includes(q.toLowerCase());
}

export function ShuttleSelect({
  id,
  choices,
  value,
  orientation,
  label,
  onChange,
}: ShuttleSelectProps): JSX.Element {
  const selectedIds = useMemo(() => asArray(value).map(String), [value]);
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  const [availFilter, setAvailFilter] = useState('');
  const [chosenFilter, setChosenFilter] = useState('');

  // Re-derive both panes from the canonical (value, choices) pair on
  // every render — no parallel state to keep in sync. Selection order
  // is preserved by following the order of `value` for the chosen
  // pane, and the natural choice order for the available pane.
  const availableChoices = useMemo(
    () => choices.filter((c) => !selectedSet.has(String(c.value))),
    [choices, selectedSet],
  );
  const chosenChoices = useMemo(() => {
    const byKey = new Map(choices.map((c) => [String(c.value), c]));
    return selectedIds.map((k) => byKey.get(k)).filter((c): c is FieldChoice => c !== undefined);
  }, [choices, selectedIds]);

  const visibleAvail = availableChoices.filter((c) => matchesFilter(c.label, availFilter));
  const visibleChosen = chosenChoices.filter((c) => matchesFilter(c.label, chosenFilter));

  function emit(next: Array<string | number>): void {
    onChange(next);
  }

  function addOne(val: string | number): void {
    if (selectedSet.has(String(val))) return;
    emit([...selectedIds.map(toOriginalType(choices)), val]);
  }

  function removeOne(val: string | number): void {
    const keep = selectedIds.filter((k) => k !== String(val));
    emit(keep.map(toOriginalType(choices)));
  }

  function addMany(targets: FieldChoice[]): void {
    const fresh: Array<string | number> = [];
    for (const c of targets) {
      const pk = pkOf(c);
      if (pk !== null && !selectedSet.has(String(pk))) fresh.push(pk);
    }
    if (fresh.length === 0) return;
    emit([...selectedIds.map(toOriginalType(choices)), ...fresh]);
  }

  function removeMany(targets: FieldChoice[]): void {
    const drop = new Set<string>();
    for (const c of targets) {
      const pk = pkOf(c);
      if (pk !== null) drop.add(String(pk));
    }
    const keep = selectedIds.filter((k) => !drop.has(k));
    emit(keep.map(toOriginalType(choices)));
  }

  const availId = `${id}-avail`;
  const chosenId = `${id}-chosen`;
  const containerClass =
    orientation === 'h'
      ? 'grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr]'
      : 'grid grid-cols-1 gap-3';

  return (
    <div className={containerClass}>
      <Pane
        title={`Available ${label}`}
        searchId={availId}
        items={visibleAvail}
        emptyMessage="No matches."
        onItemActivate={(c) => {
          const pk = pkOf(c);
          if (pk !== null) addOne(pk);
        }}
        actionLabel="Choose all"
        onAction={() => addMany(visibleAvail)}
        filter={availFilter}
        setFilter={setAvailFilter}
      />
      <Pane
        title={`Chosen ${label}`}
        searchId={chosenId}
        items={visibleChosen}
        emptyMessage="Nothing selected yet."
        onItemActivate={(c) => {
          const pk = pkOf(c);
          if (pk !== null) removeOne(pk);
        }}
        actionLabel="Remove all"
        onAction={() => removeMany(visibleChosen)}
        filter={chosenFilter}
        setFilter={setChosenFilter}
      />
    </div>
  );
}

/** Map stringified pk back to the choice's original value type so
 *  numeric pks round-trip as numbers (matches the legacy M2M path).
 *  Boolean / null choice values can't be M2M pks; filtered out so
 *  the Map's value type stays narrow. */
function toOriginalType(
  choices: FieldChoice[],
): (str: string) => string | number {
  const entries: Array<[string, string | number]> = [];
  for (const c of choices) {
    if (typeof c.value === 'string' || typeof c.value === 'number') {
      entries.push([String(c.value), c.value]);
    }
  }
  const map = new Map(entries);
  return (s) => map.get(s) ?? s;
}

interface PaneProps {
  title: string;
  searchId: string;
  items: FieldChoice[];
  emptyMessage: string;
  onItemActivate: (c: FieldChoice) => void;
  actionLabel: string;
  onAction: () => void;
  filter: string;
  setFilter: (v: string) => void;
}

function Pane({
  title,
  searchId,
  items,
  emptyMessage,
  onItemActivate,
  actionLabel,
  onAction,
  filter,
  setFilter,
}: PaneProps): JSX.Element {
  const titleId = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <div id={titleId} className="text-sm font-medium text-gray-700">
        {title}
      </div>
      <label htmlFor={searchId} className="sr-only">
        Filter {title}
      </label>
      <input
        id={searchId}
        type="search"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter"
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-gray-500"
      />
      <ul
        role="listbox"
        aria-labelledby={titleId}
        className="h-48 overflow-y-auto rounded border border-gray-300 bg-white"
      >
        {items.length === 0 ? (
          <li className="px-2 py-1.5 text-sm italic text-gray-500">{emptyMessage}</li>
        ) : (
          items.map((c) => (
            <li
              key={String(c.value)}
              role="option"
              aria-selected={false}
              tabIndex={0}
              onClick={() => onItemActivate(c)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onItemActivate(c);
                }
              }}
              className="cursor-pointer px-2 py-1 text-sm hover:bg-gray-50 focus:bg-gray-100 focus:outline-none"
            >
              {c.label}
            </li>
          ))
        )}
      </ul>
      <button
        type="button"
        onClick={onAction}
        disabled={items.length === 0}
        className="self-start text-xs text-gray-600 hover:text-gray-900 disabled:cursor-not-allowed disabled:text-gray-400"
      >
        {actionLabel}
      </button>
    </div>
  );
}
