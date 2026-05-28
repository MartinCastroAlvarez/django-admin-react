// FilterBar — the list-view search input + inline per-filter dropdown
// buttons (replaces the old filter modal). Each filter is a button that
// opens a small options popover; an active filter shows a count badge and
// a highlighted button. Single-select per filter, matching Django's
// list_filter. Presentational + callback-driven — the page owns the URL
// state and passes the current values + change handlers in.
//
// Layout: leading + search + filters + trailing all live on one row. The
// trailing slot is pinned right (the page composes it so the row ends in
// "Clear all" then "Customize").

import {
  Children,
  cloneElement,
  isValidElement,
  useEffect,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react';
import { Check, ChevronDown } from 'lucide-react';

import type { FilterDescriptor, FilterOption } from '@dar/data';
import { Input, Popover } from '@dar/ui';

// Above this many options a dropdown gets a typeahead box — below it,
// scanning is faster than typing and a search field would just be
// redundant chrome (CLAUDE.md §7).
const FILTER_SEARCH_THRESHOLD = 8;

export interface FilterBarProps {
  /** Show the search input (e.g. the model has `search_fields`). */
  showSearch?: boolean;
  searchValue: string;
  onSearchChange: (q: string) => void;
  /** Commit search immediately (on blur / Enter), in addition to the
   *  page's debounce. Optional. */
  onSearchCommit?: () => void;
  searchPlaceholder?: string;
  /** `ModelAdmin.search_help_text`, shown under the search box. */
  searchHelpText?: string | null;
  filters: FilterDescriptor[];
  /** Active selections, keyed by filter `name` → selected value. */
  active: Record<string, string>;
  /** Set/clear one filter — pass '' to clear it. */
  onFilterChange: (name: string, value: string) => void;
  /** Controls rendered to the **left** of the search input (e.g. the
   *  bulk-actions menu, which sits before search when rows are selected). */
  leading?: ReactNode;
  /** Right-aligned controls on the same row (the page composes these:
   *  "Clear all" then the column customizer). */
  trailing?: ReactNode;
}

function optionsFor(filter: FilterDescriptor): FilterOption[] {
  if (filter.type === 'boolean') {
    return [
      { value: 'true', label: 'Yes' },
      { value: 'false', label: 'No' },
    ];
  }
  return filter.lookups ?? filter.choices ?? [];
}

export function FilterBar({
  showSearch = true,
  searchValue,
  onSearchChange,
  onSearchCommit,
  searchPlaceholder = 'Search…',
  searchHelpText,
  filters,
  active,
  onFilterChange,
  leading,
  trailing,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {leading}
      {showSearch && (
        <form
          className="min-w-[12rem] flex-1 sm:max-w-xs"
          onSubmit={(e) => {
            e.preventDefault();
            onSearchCommit?.();
          }}
        >
          <Input
            value={searchValue}
            placeholder={searchPlaceholder}
            aria-label="Search"
            aria-describedby={searchHelpText ? 'dar-search-help' : undefined}
            onChange={(e) => onSearchChange(e.target.value)}
            onBlur={() => onSearchCommit?.()}
          />
          {searchHelpText ? (
            <p id="dar-search-help" className="mt-1 text-xs text-gray-500">
              {searchHelpText}
            </p>
          ) : null}
        </form>
      )}
      {filters.map((f) => (
        <FilterDropdown
          key={f.name}
          filter={f}
          // Fall back to the descriptor's server-applied `selected` (a
          // SimpleListFilter default) when the URL carries no value, so
          // the control reflects the rows actually returned (#283).
          value={active[f.name] ?? (f.selected != null ? String(f.selected) : '')}
          onChange={(v) => onFilterChange(f.name, v)}
        />
      ))}
      {/* Trailing slot (#554, #570): rendered as DIRECT children of the
          outer flex-wrap container — not inside a sub-wrapper — so the
          trailing buttons participate in the same wrap pass as the
          filter pills and stay glued to the end of the last pill row.
          `ml-auto` is injected on the first non-null trailing child to
          push the cluster to the row's right edge; if a wrap occurs the
          trailing items wrap WITH the pills, never as a separate row.
          A sub-wrapper here would behave as one flex item and produce
          the "buttons on their own line" symptom #570 reported. */}
      {(() => {
        const items = Children.toArray(trailing).filter(Boolean);
        let firstReal = true;
        return items.map((child, i) => {
          if (!isValidElement<{ className?: string }>(child)) return child;
          const isFirst = firstReal;
          firstReal = false;
          const extra = isFirst ? ' ml-auto' : '';
          return cloneElement(child, {
            className: `${child.props.className ?? ''}${extra}`,
            key: child.key ?? i,
          });
        });
      })()}
    </div>
  );
}

interface FilterDropdownProps {
  filter: FilterDescriptor;
  value: string;
  onChange: (value: string) => void;
}

function FilterDropdown({ filter, value, onChange }: FilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const opts = optionsFor(filter);
  const selectedLabel = value
    ? (opts.find((o) => String(o.value) === value)?.label ?? value)
    : null;

  const select = (v: string): void => {
    onChange(v);
    setOpen(false);
  };

  const trigger = (
    <button
      type="button"
      onClick={() => setOpen((o) => !o)}
      aria-expanded={open}
      className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
        value ? 'border-primary bg-blue-50 text-primary' : 'border-gray-300 hover:bg-gray-100'
      }`}
    >
      <span>{filter.label}</span>
      {selectedLabel ? (
        <span className="rounded bg-primary px-1.5 text-xs font-medium text-white">1</span>
      ) : null}
      <ChevronDown className="h-3.5 w-3.5 shrink-0" aria-hidden />
    </button>
  );

  return (
    <Popover open={open} onClose={() => setOpen(false)} trigger={trigger} panelClassName="min-w-[14rem]">
      {filter.type === 'date' ? (
        <div className="p-2">
          <input
            type="date"
            value={value}
            onChange={(e) => select(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
          />
          {value ? (
            <button
              type="button"
              onClick={() => select('')}
              className="mt-2 text-xs text-gray-500 hover:underline"
            >
              Clear
            </button>
          ) : null}
        </div>
      ) : (
        <FilterOptions filterLabel={filter.label} opts={opts} value={value} onSelect={select} />
      )}
    </Popover>
  );
}

interface FilterOptionsProps {
  filterLabel: string;
  opts: FilterOption[];
  value: string;
  onSelect: (value: string) => void;
}

// The option list inside a filter dropdown. With enough options it gets a
// typeahead box: typing narrows to the matching options (only valid
// matches stay selectable), and ↑/↓ + Enter or Tab move through them so
// the operator can search the filter's values quickly without the mouse.
function FilterOptions({ filterLabel, opts, value, onSelect }: FilterOptionsProps) {
  const showSearch = opts.length >= FILTER_SEARCH_THRESHOLD;
  const [query, setQuery] = useState('');
  const norm = query.trim().toLowerCase();
  const matches = norm ? opts.filter((o) => o.label.toLowerCase().includes(norm)) : opts;
  // Navigable list: "All" (clear) first, then the matching options.
  const items: FilterOption[] = [{ value: '', label: 'All' }, ...matches];
  const [highlight, setHighlight] = useState(0);

  // When a query is active, pre-highlight the first real match (so Enter
  // accepts it); with no query, rest on "All". Re-runs as the list narrows.
  useEffect(() => {
    setHighlight(norm && matches.length > 0 ? 1 : 0);
  }, [norm, matches.length]);

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (items.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const it = items[highlight];
      if (it) onSelect(String(it.value));
    } else if (e.key === 'Tab') {
      // Tab → next valid match (Shift+Tab → previous), wrapping. Trapped
      // here so the operator can scan matches without leaving the field.
      e.preventDefault();
      setHighlight((h) => (h + (e.shiftKey ? items.length - 1 : 1)) % items.length);
    }
  };

  return (
    <div>
      {showSearch ? (
        <div className="border-b border-gray-200 p-2">
          <input
            type="text"
            // The popover just opened expressly to filter, so focusing the
            // box is the point — the operator can type immediately.
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type to filter…"
            aria-label={`Filter ${filterLabel} options`}
            className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          />
        </div>
      ) : null}
      <ul className="max-h-72 overflow-auto py-1">
        {items.map((it, i) => {
          const v = String(it.value);
          const isAll = v === '';
          const selected = isAll ? value === '' : v === value;
          const active = showSearch && i === highlight;
          return (
            <li key={isAll ? '__all__' : v}>
              <button
                type="button"
                onClick={() => onSelect(v)}
                className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-gray-100 ${
                  active ? 'bg-gray-100' : ''
                } ${selected ? 'font-medium text-primary' : 'text-gray-700'}`}
              >
                {selected ? (
                  <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />
                ) : (
                  <span className="w-3.5 shrink-0" />
                )}
                <span className="truncate">{it.label}</span>
              </button>
            </li>
          );
        })}
        {showSearch && matches.length === 0 ? (
          <li className="px-3 py-2 text-sm text-gray-400">No matches.</li>
        ) : null}
      </ul>
    </div>
  );
}
