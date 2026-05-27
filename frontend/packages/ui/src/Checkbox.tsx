// Styled checkbox primitive. The native checkbox is intentionally
// excluded from the app's dark-mode input remap (it keeps its OS accent),
// which leaves a bright native box that clashes with the themed form
// controls. This renders an `appearance-none` box styled to match the
// text inputs — same border, the same surface (transparent, so it picks
// up the card/table background in both themes exactly like an input) —
// with a primary fill + check mark when checked. Generic, props-driven:
// no business knowledge (CLAUDE.md §7). The check is an inline SVG so
// @dar/ui stays free of an icon-library dependency.

import type { InputHTMLAttributes } from 'react';

export type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>;

export function Checkbox({ className = '', ...rest }: CheckboxProps) {
  return (
    <span className="relative inline-flex h-4 w-4 shrink-0 align-middle">
      <input
        type="checkbox"
        className={`peer h-4 w-4 cursor-pointer appearance-none rounded border border-gray-300 bg-transparent transition-colors checked:border-primary checked:bg-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        {...rest}
      />
      {/* Tick shows only when the box is checked (peer-checked); white
          reads on the primary fill. pointer-events-none so the click
          falls through to the input underneath. */}
      <svg
        className="pointer-events-none absolute inset-0 m-auto hidden h-3 w-3 text-white peer-checked:block"
        viewBox="0 0 12 12"
        fill="none"
        aria-hidden
      >
        <path
          d="M2.5 6.5 5 9l4.5-5"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}
