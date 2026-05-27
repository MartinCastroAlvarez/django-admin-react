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

import { useState, type ReactNode } from 'react';
import { Check, ChevronDown } from 'lucide-react';

import type { FilterDescriptor, FilterOption } from '@dar/data';
import { Input, Popover } from '@dar/ui';

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
      {trailing ? <div className="ml-auto flex flex-wrap items-center gap-2">{trailing}</div> : null}
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
        <ul className="max-h-72 overflow-auto py-1">
          <li>
            <button
              type="button"
              onClick={() => select('')}
              className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-gray-100 ${
                value ? 'text-gray-700' : 'font-medium text-primary'
              }`}
            >
              {value ? <span className="w-3.5 shrink-0" /> : <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />}
              All
            </button>
          </li>
          {opts.map((o) => {
            const v = String(o.value);
            const selected = v === value;
            return (
              <li key={v}>
                <button
                  type="button"
                  onClick={() => select(v)}
                  className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-gray-100 ${
                    selected ? 'font-medium text-primary' : 'text-gray-700'
                  }`}
                >
                  {selected ? (
                    <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  ) : (
                    <span className="w-3.5 shrink-0" />
                  )}
                  <span className="truncate">{o.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Popover>
  );
}
